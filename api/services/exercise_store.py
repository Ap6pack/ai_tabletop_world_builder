#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Redis-backed storage for multi-team exercise state with file-based fallback."""
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timezone

from api.models.exercise_models import ExerciseState
from api.utils.logger import setup_logger

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

    def __init__(self, redis_url: Optional[str] = None) -> None:
        """
        Initialize the exercise store.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0").
                       If None or connection fails, falls back to file storage.
        """
        self._use_redis = False
        self._redis_client: Optional["redis.Redis"] = None
        self._storage_dir = Path("data/exercises")
        self._archive_dir = Path("data/exercises/archive")

        # Ensure file-based directories exist
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._archive_dir.mkdir(parents=True, exist_ok=True)

        # Attempt Redis connection
        if redis_url and REDIS_AVAILABLE:
            try:
                self._redis_client = redis.Redis.from_url(
                    redis_url, decode_responses=True
                )
                self._redis_client.ping()
                self._use_redis = True
                logger.info("ExerciseStore initialized with Redis backend: %s", redis_url)
            except (redis.ConnectionError, redis.RedisError) as exc:
                logger.warning(
                    "Redis connection failed (%s), falling back to file storage.",
                    exc,
                )
                self._redis_client = None
                self._use_redis = False
        elif redis_url and not REDIS_AVAILABLE:
            logger.warning(
                "redis-py package not installed. Falling back to file storage."
            )
        else:
            logger.info("No Redis URL provided. Using file-based exercise storage.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_exercise(self, exercise_id: str) -> Optional[ExerciseState]:
        """
        Load an exercise by ID.

        Args:
            exercise_id: The unique exercise identifier.

        Returns:
            ExerciseState if found, otherwise None.
        """
        if self._use_redis:
            return self._redis_get(exercise_id)
        return self._file_get(exercise_id)

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
            self._file_save(state)

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
        return self._file_delete(exercise_id)

    def list_exercises(self, phase: Optional[str] = None) -> List[Dict]:
        """
        List exercises with summary information.

        Args:
            phase: Optional filter (e.g., "active", "completed").

        Returns:
            List of dicts with keys: exercise_id, name, phase, team_count,
            current_round, version.
        """
        if self._use_redis:
            summaries = self._redis_list()
        else:
            summaries = self._file_list()

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
        archive_path.write_text(
            state.model_dump_json(indent=2), encoding="utf-8"
        )

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
        return self._file_get_version(exercise_id)

    # ------------------------------------------------------------------
    # Redis backend
    # ------------------------------------------------------------------

    def _redis_key(self, exercise_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}{exercise_id}"

    def _redis_get(self, exercise_id: str) -> Optional[ExerciseState]:
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

    def _redis_list(self) -> List[Dict]:
        summaries: List[Dict] = []
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor, match=f"{REDIS_KEY_PREFIX}*", count=100
                )
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

    def _file_get(self, exercise_id: str) -> Optional[ExerciseState]:
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
            path.write_text(
                state.model_dump_json(indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.error("Failed to save exercise to %s: %s", path, exc)

    def _file_delete(self, exercise_id: str) -> bool:
        path = self._file_path(exercise_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def _file_list(self) -> List[Dict]:
        summaries: List[Dict] = []
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
    def _make_summary(state: ExerciseState) -> Dict:
        """Build a lightweight summary dict from full exercise state."""
        return {
            "exercise_id": state.exercise_id,
            "name": state.name,
            "phase": state.phase,
            "team_count": len(state.teams),
            "current_round": state.current_round,
            "version": state.version,
        }
