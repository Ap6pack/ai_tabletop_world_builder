#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Give a user ownership of records that have no owner.

Game sessions, generated scenarios and exercises created before per-user
ownership existed (or while REQUIRE_AUTH was off) have no owner, so with auth
on only admins can see them. This hands all such records to one user.

Usage:
    python scripts/assign_owner.py <username> [--dry-run]

Reads DATABASE_URL from the environment/.env like the app.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from api.db import ExerciseRow, GameSessionRow, GeneratedScenarioRow, UserRow, init_db, session_scope  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign unowned records to a user.")
    parser.add_argument("username")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would change")
    args = parser.parse_args()

    init_db()
    with session_scope() as db:
        user = db.scalar(select(UserRow).where(UserRow.username == args.username))
        if user is None:
            print(f"User '{args.username}' not found.")
            return 1

        counts = {}
        for label, model, mirror_in_data in (
            ("game sessions", GameSessionRow, True),
            ("generated scenarios", GeneratedScenarioRow, False),
            ("exercises", ExerciseRow, True),
        ):
            rows = db.scalars(select(model).where(model.owner_id.is_(None))).all()
            counts[label] = len(rows)
            if args.dry_run:
                continue
            for row in rows:
                row.owner_id = user.id
                if mirror_in_data:
                    # The JSON payload carries owner_id too; keep them in sync.
                    row.data = {**row.data, "owner_id": user.id}
                    if model is ExerciseRow and isinstance(row.data.get("game_state"), dict):
                        row.data = {**row.data, "game_state": {**row.data["game_state"], "owner_id": user.id}}
        if args.dry_run:
            db.rollback()

    verb = "Would assign" if args.dry_run else "Assigned"
    for label, n in counts.items():
        print(f"{verb} {n} {label} to {args.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
