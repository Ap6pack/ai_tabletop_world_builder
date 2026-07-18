#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
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
