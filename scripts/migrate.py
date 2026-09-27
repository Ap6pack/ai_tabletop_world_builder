#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Bring the database schema up to date (run by the container entrypoint).

Databases created by v1.0.0 containers were built with ``create_all`` and have
no ``alembic_version`` table. Their schema matches the initial migration, so
they are stamped at that revision first and then upgraded normally.

Usage:
    python scripts/migrate.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402

from alembic import command  # noqa: E402
from config.settings import settings  # noqa: E402

INITIAL_REVISION = "22a7073a83cb"


def main() -> int:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))

    engine = create_engine(settings.database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    if "alembic_version" not in tables and "users" in tables:
        print(f"Existing database without migration history; stamping {INITIAL_REVISION}.")
        command.stamp(cfg, INITIAL_REVISION)
    command.upgrade(cfg, "head")
    print("Database schema is up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
