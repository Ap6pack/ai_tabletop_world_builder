#!/bin/bash
set -e

mkdir -p /app/data/sessions /app/data/users /app/data/audit_logs /app/data/library /app/data/webhooks /app/data/api_keys /app/scenarios/generated /app/scenarios/templates

exec "$@"
