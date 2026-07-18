#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Promote an existing user to the ``admin`` role.

Usage:
    python scripts/create_admin.py <username>

The user must already exist (register via the UI or POST /auth/register first).
Reads DATABASE_URL from the environment/.env like the app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from api.db import UserRow, init_db, session_scope  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_admin.py <username>")
        return 2

    username = sys.argv[1]
    init_db()
    with session_scope() as db:
        user = db.scalar(select(UserRow).where(UserRow.username == username))
        if user is None:
            print(f"User '{username}' not found. Register the user first.")
            return 1
        user.role = "admin"
        print(f"User '{username}' (id={user.id}) is now an admin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
