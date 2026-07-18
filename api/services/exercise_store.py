#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Storage for multi-team exercise state.

Defaults to the application database. Redis can be enabled as a low-latency
fast-path via ``redis_url``; a file backend remains for archival and as a
last-resort fallback.
"""

import json
from pathlib import Path

from sqlalchemy import select

from api.db import ExerciseRow, init_db, session_scope
from api.models.exercise_models import ExerciseState
from api.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Default TTL for Redis keys: 24 hours
REDIS_TTL_SECONDS = 86400
REDIS_KEY_PREFIX = "exercise:"


class ExerciseStore:
    """
    Storage backend for multi-team exercise state.

    Attempts to use Redis for low-latency, shared-state access.
    Falls back to file-based JSON storage if Redis is unavailable.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """
        Initialize the exercise store.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0").
                       Defaults to ``settings.redis_url``. If empty/None or the
                       connection fails, exercise state is served from the
                       database.
        """
        if redis_url is None:
            redis_url = settings.redis_url or None

        self._use_redis = False
        self._redis_client: redis.Redis | None = None
        self._storage_dir = Path("data/exercises")
        self._archive_dir = Path("data/exercises/archive")

        # Ensure the database schema and the file archive directory exist.
        init_db()
        self._archive_dir.mkdir(parents=True, exist_ok=True)

        # Attempt Redis connection
        if redis_url and REDIS_AVAILABLE:
            try:
                self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                self._use_redis = True
                logger.info("ExerciseStore initialized with Redis backend: %s", redis_url)
            except (redis.ConnectionError, redis.RedisError) as exc:
                logger.warning(
                    "Redis connection failed (%s), falling back to database storage.",
                    exc,
                )
                self._redis_client = None
                self._use_redis = False
        elif redis_url and not REDIS_AVAILABLE:
            logger.warning("redis-py package not installed. Falling back to database storage.")
        else:
            logger.info("No Redis URL provided. Using database exercise storage.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_exercise(self, exercise_id: str) -> ExerciseState | None:
        """
        Load an exercise by ID.

        Args:
            exercise_id: The unique exercise identifier.

        Returns:
            ExerciseState if found, otherwise None.
        """
        if self._use_redis:
            return self._redis_get(exercise_id)
        return self._db_get(exercise_id)

    def save_exercise(self, state: ExerciseState) -> None:
        """
        Persist the exercise state.

        The version counter is incremented automatically before saving so
        that polling clients can detect changes.

        Args:
            state: The exercise state to save.
        """
        state.version += 1

        if self._use_redis:
            self._redis_save(state)
        else:
            self._db_save(state)

        logger.debug(
            "Saved exercise %s (version %d, phase=%s)",
            state.exercise_id,
            state.version,
            state.phase,
        )

    def delete_exercise(self, exercise_id: str) -> bool:
        """
        Remove an exercise from storage.

        Args:
            exercise_id: The exercise to delete.

        Returns:
            True if the exercise existed and was deleted.
        """
        if self._use_redis:
            return self._redis_delete(exercise_id)
        return self._db_delete(exercise_id)

    def list_exercises(self, phase: str | None = None) -> list[dict]:
        """
        List exercises with summary information.

        Args:
            phase: Optional filter (e.g., "active", "completed").

        Returns:
            List of dicts with keys: exercise_id, name, phase, team_count,
            current_round, version.
        """
        summaries = self._redis_list() if self._use_redis else self._db_list()

        if phase:
            summaries = [s for s in summaries if s.get("phase") == phase]

        return summaries

    def archive_exercise(self, exercise_id: str) -> str:
        """
        Move an exercise to permanent archive storage.

        For Redis-backed exercises this means writing to the file archive
        and removing the Redis key.  For file-backed exercises the JSON
        file is moved into the archive sub-directory.

        Args:
            exercise_id: The exercise to archive.

        Returns:
            The file path of the archived exercise.

        Raises:
            ValueError: If the exercise does not exist.
        """
        state = self.get_exercise(exercise_id)
        if state is None:
            raise ValueError(f"Exercise {exercise_id} not found.")

        archive_path = self._archive_dir / f"{exercise_id}.json"
        archive_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

        # Remove from primary storage
        self.delete_exercise(exercise_id)

        logger.info("Archived exercise %s to %s", exercise_id, archive_path)
        return str(archive_path)

    def get_exercise_version(self, exercise_id: str) -> int:
        """
        Return the current version number without loading full state.

        Useful for lightweight polling to detect changes.

        Args:
            exercise_id: The exercise to check.

        Returns:
            The version number, or -1 if the exercise does not exist.
        """
        if self._use_redis:
            return self._redis_get_version(exercise_id)
        return self._db_get_version(exercise_id)

    # ------------------------------------------------------------------
    # Database backend (default)
    # ------------------------------------------------------------------

    def _db_get(self, exercise_id: str) -> ExerciseState | None:
        with session_scope() as db:
            row = db.get(ExerciseRow, exercise_id)
            if row is None:
                return None
            return ExerciseState.model_validate(row.data)

    def _db_save(self, state: ExerciseState) -> None:
        payload = state.model_dump(mode="json")
        with session_scope() as db:
            row = db.get(ExerciseRow, state.exercise_id)
            if row is None:
                row = ExerciseRow(exercise_id=state.exercise_id)
                db.add(row)
            row.name = state.name
            row.phase = state.phase
            row.facilitator_id = state.facilitator_id
            row.current_round = state.current_round
            row.team_count = len(state.teams)
            row.version = state.version
            row.data = payload

    def _db_delete(self, exercise_id: str) -> bool:
        with session_scope() as db:
            row = db.get(ExerciseRow, exercise_id)
            if row is None:
                return False
            db.delete(row)
        return True

    def _db_list(self) -> list[dict]:
        with session_scope() as db:
            rows = db.scalars(select(ExerciseRow)).all()
            return [
                {
                    "exercise_id": row.exercise_id,
                    "name": row.name,
                    "phase": row.phase,
                    "team_count": row.team_count,
                    "current_round": row.current_round,
                    "version": row.version,
                }
                for row in rows
            ]

    def _db_get_version(self, exercise_id: str) -> int:
        with session_scope() as db:
            version = db.scalar(select(ExerciseRow.version).where(ExerciseRow.exercise_id == exercise_id))
            return version if version is not None else -1

    # ------------------------------------------------------------------
    # Redis backend
    # ------------------------------------------------------------------

    def _redis_key(self, exercise_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}{exercise_id}"

    def _redis_get(self, exercise_id: str) -> ExerciseState | None:
        try:
            data = self._redis_client.get(self._redis_key(exercise_id))
            if data is None:
                return None
            return ExerciseState.model_validate_json(data)
        except Exception as exc:
            logger.error("Redis GET failed for %s: %s", exercise_id, exc)
            return None

    def _redis_save(self, state: ExerciseState) -> None:
        try:
            self._redis_client.setex(
                self._redis_key(state.exercise_id),
                REDIS_TTL_SECONDS,
                state.model_dump_json(),
            )
        except Exception as exc:
            logger.error(
                "Redis SET failed for %s: %s. Falling back to file.",
                state.exercise_id,
                exc,
            )
            self._file_save(state)

    def _redis_delete(self, exercise_id: str) -> bool:
        try:
            removed = self._redis_client.delete(self._redis_key(exercise_id))
            return removed > 0
        except Exception as exc:
            logger.error("Redis DELETE failed for %s: %s", exercise_id, exc)
            return False

    def _redis_list(self) -> list[dict]:
        summaries: list[dict] = []
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(cursor=cursor, match=f"{REDIS_KEY_PREFIX}*", count=100)
                for key in keys:
                    data = self._redis_client.get(key)
                    if data:
                        try:
                            state = ExerciseState.model_validate_json(data)
                            summaries.append(self._make_summary(state))
                        except Exception:
                            logger.warning("Skipping corrupt exercise key: %s", key)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.error("Redis SCAN failed: %s", exc)
        return summaries

    def _redis_get_version(self, exercise_id: str) -> int:
        try:
            data = self._redis_client.get(self._redis_key(exercise_id))
            if data is None:
                return -1
            # Parse just enough to get version
            state = ExerciseState.model_validate_json(data)
            return state.version
        except Exception as exc:
            logger.error("Redis version check failed for %s: %s", exercise_id, exc)
            return -1

    # ------------------------------------------------------------------
    # File backend
    # ------------------------------------------------------------------

    def _file_path(self, exercise_id: str) -> Path:
        return self._storage_dir / f"{exercise_id}.json"

    def _file_get(self, exercise_id: str) -> ExerciseState | None:
        path = self._file_path(exercise_id)
        if not path.exists():
            return None
        try:
            data = path.read_text(encoding="utf-8")
            return ExerciseState.model_validate_json(data)
        except Exception as exc:
            logger.error("Failed to load exercise from %s: %s", path, exc)
            return None

    def _file_save(self, state: ExerciseState) -> None:
        path = self._file_path(state.exercise_id)
        try:
            path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to save exercise to %s: %s", path, exc)

    def _file_delete(self, exercise_id: str) -> bool:
        path = self._file_path(exercise_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def _file_list(self) -> list[dict]:
        summaries: list[dict] = []
        for path in self._storage_dir.glob("*.json"):
            try:
                data = path.read_text(encoding="utf-8")
                state = ExerciseState.model_validate_json(data)
                summaries.append(self._make_summary(state))
            except Exception:
                logger.warning("Skipping corrupt exercise file: %s", path)
        return summaries

    def _file_get_version(self, exercise_id: str) -> int:
        path = self._file_path(exercise_id)
        if not path.exists():
            return -1
        try:
            data = path.read_text(encoding="utf-8")
            parsed = json.loads(data)
            return parsed.get("version", -1)
        except Exception as exc:
            logger.error("Failed to read version from %s: %s", path, exc)
            return -1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_summary(state: ExerciseState) -> dict:
        """Build a lightweight summary dict from full exercise state."""
        return {
            "exercise_id": state.exercise_id,
            "name": state.name,
            "phase": state.phase,
            "team_count": len(state.teams),
            "current_round": state.current_round,
            "version": state.version,
        }
