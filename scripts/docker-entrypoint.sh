#!/bin/bash
set -e

# All application state, including the audit log, lives in the database.
mkdir -p /app/data

# Apply schema migrations before starting (set SKIP_MIGRATIONS=1 to skip,
# e.g. when a separate job runs them).
if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
    python /app/scripts/migrate.py
fi

exec "$@"
