#!/bin/bash
set -e

# Users, sessions, exercises, keys, webhooks, and scenarios are database-backed.
# Only the append-only audit log and the local SQLite dir remain file-based.
mkdir -p /app/data/audit_logs

exec "$@"
