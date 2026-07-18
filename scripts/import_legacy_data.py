#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Import legacy file-based data into the database.

Earlier versions stored users, sessions, exercises, API keys, webhooks, and
scenarios as JSON files. This one-time script upserts that data into the
database (keyed by primary key, so it is safe to re-run).

Usage:
    alembic upgrade head
    python scripts/import_legacy_data.py [--data-dir data] [--scenarios-dir scenarios/generated]
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.db import (  # noqa: E402
    ApiKeyRow,
    ExerciseRow,
    GameSessionRow,
    GeneratedScenarioRow,
    LibraryScenarioRow,
    UserRow,
    WebhookDeliveryRow,
    WebhookRow,
    init_db,
    session_scope,
)


def _read_json_files(directory: Path):
    """Yield (path, data) for each readable *.json file in a directory."""
    if not directory.exists():
        return
    for path in sorted(directory.glob("*.json")):
        try:
            yield path, json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ! skipping {path.name}: {exc}")


def _import_users(db, data_dir: Path) -> int:
    count = 0
    for _path, d in _read_json_files(data_dir / "users"):
        if not d.get("id"):
            continue
        row = db.get(UserRow, d["id"]) or UserRow(id=d["id"])
        row.username = d.get("username", "")
        row.email = d.get("email", "")
        row.display_name = d.get("display_name", "")
        row.hashed_password = d.get("hashed_password", "")
        row.created_at = d.get("created_at", datetime.now(UTC).isoformat())
        row.role = d.get("role", "user")
        row.is_active = d.get("is_active", True)
        db.merge(row)
        count += 1
    return count


def _import_sessions(db, data_dir: Path) -> int:
    count = 0
    for path, d in _read_json_files(data_dir / "sessions"):
        session_id = d.get("session_id") or path.stem
        row = db.get(GameSessionRow, session_id) or GameSessionRow(session_id=session_id)
        timeline = d.get("incident_timeline") or []
        row.status = d.get("status", "in-progress")
        row.player_role = d.get("player_role")
        row.org_name = (d.get("organization") or {}).get("name")
        row.score = d.get("score", 0)
        row.time_elapsed = d.get("time_elapsed", 0)
        row.created_at = timeline[0].get("timestamp") if timeline else None
        row.data = d
        db.merge(row)
        count += 1
    return count


def _import_exercises(db, data_dir: Path) -> int:
    count = 0
    for path, d in _read_json_files(data_dir / "exercises"):
        exercise_id = d.get("exercise_id") or path.stem
        row = db.get(ExerciseRow, exercise_id) or ExerciseRow(exercise_id=exercise_id)
        row.name = d.get("name", "")
        row.phase = d.get("phase", "setup")
        row.facilitator_id = d.get("facilitator_id")
        row.current_round = d.get("current_round", 0)
        row.team_count = len(d.get("teams", []))
        row.version = d.get("version", 0)
        row.data = d
        db.merge(row)
        count += 1
    return count


def _import_api_keys(db, data_dir: Path) -> int:
    count = 0
    for _path, d in _read_json_files(data_dir / "api_keys"):
        if not d.get("id"):
            continue
        row = db.get(ApiKeyRow, d["id"]) or ApiKeyRow(id=d["id"])
        row.user_id = d.get("user_id", "")
        row.name = d.get("name", "")
        row.hashed_key = d.get("hashed_key", "")
        row.prefix = d.get("prefix", "")
        row.scopes = d.get("scopes", [])
        row.created_at = d.get("created_at", datetime.now(UTC).isoformat())
        row.revoked = d.get("revoked", False)
        row.revoked_at = d.get("revoked_at")
        db.merge(row)
        count += 1
    return count


def _import_webhooks(db, data_dir: Path) -> int:
    count = 0
    webhooks_dir = data_dir / "webhooks"
    for path, d in _read_json_files(webhooks_dir):
        if path.name.endswith("_deliveries.json") or not d.get("id"):
            continue
        row = db.get(WebhookRow, d["id"]) or WebhookRow(id=d["id"])
        row.url = d.get("url", "")
        row.events = d.get("events", [])
        row.user_id = d.get("user_id", "system")
        row.active = d.get("active", True)
        row.secret = d.get("secret")
        row.created_at = d.get("created_at", datetime.now(UTC).isoformat())
        db.merge(row)
        count += 1
        # Delivery logs (a JSON list) for this webhook.
        log_path = webhooks_dir / f"{d['id']}_deliveries.json"
        if log_path.exists():
            try:
                for record in json.loads(log_path.read_text()):
                    db.add(WebhookDeliveryRow(webhook_id=d["id"], record=record))
            except (json.JSONDecodeError, OSError):
                pass
    return count


def _import_generated_scenarios(db, scenarios_dir: Path) -> int:
    count = 0
    for path, d in _read_json_files(scenarios_dir):
        row = db.get(GeneratedScenarioRow, path.name) or GeneratedScenarioRow(filename=path.name)
        row.name = d.get("name", "")
        row.industry = d.get("industry")
        row.size = d.get("size")
        row.created_at = datetime.fromtimestamp(path.stat().st_ctime, tz=UTC).isoformat()
        row.data = d
        db.merge(row)
        count += 1
    return count


def _import_library(db, data_dir: Path) -> int:
    count = 0
    for path, d in _read_json_files(data_dir / "library"):
        scenario_id = d.get("id") or path.stem
        row = db.get(LibraryScenarioRow, scenario_id) or LibraryScenarioRow(id=scenario_id)
        row.category = d.get("category")
        row.difficulty = d.get("difficulty")
        row.rating = d.get("rating", 0.0)
        row.rating_count = d.get("rating_count", 0)
        row.created_at = d.get("created_at", datetime.now(UTC).isoformat())
        row.data = d
        db.merge(row)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy file-based data into the database.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--scenarios-dir", default="scenarios/generated")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    scenarios_dir = Path(args.scenarios_dir)

    init_db()
    with session_scope() as db:
        results = {
            "users": _import_users(db, data_dir),
            "sessions": _import_sessions(db, data_dir),
            "exercises": _import_exercises(db, data_dir),
            "api_keys": _import_api_keys(db, data_dir),
            "webhooks": _import_webhooks(db, data_dir),
            "generated_scenarios": _import_generated_scenarios(db, scenarios_dir),
            "library_scenarios": _import_library(db, data_dir),
        }

    print("Imported:")
    for store, n in results.items():
        print(f"  {store}: {n}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
