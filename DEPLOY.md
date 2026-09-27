# Deployment Guide

This guide covers deploying the Cybersecurity War Gaming Platform for a public,
multi-user environment. For local development see the README.

## Overview

- **API**: FastAPI (`main:app`), stateless — scale horizontally behind a load balancer.
- **Frontend**: Streamlit (`app/Home.py`).
- **Database**: PostgreSQL (required for production). All mutable state lives here.
- **Cache**: Redis — shared rate-limit counters (required with more than one
  worker or instance) and a low-latency fast-path for live multi-team exercises.

## 1. Prerequisites

- Python 3.11, 3.12 or 3.13
- A managed PostgreSQL database (RDS, Cloud SQL, Neon, Supabase, …)
- Redis (required when running more than one worker or instance)
- An API key for at least one LLM provider (OpenAI, Anthropic, Together, or a
  self-hosted Ollama)

## 2. Configuration

Set these as environment variables (never commit real secrets). See
`.env.example` for the full list.

| Variable | Purpose | Production value |
|---|---|---|
| `DATABASE_URL` | Database connection | `postgresql+psycopg://user:pass@host:5432/db` |
| `REQUIRE_AUTH` | Enforce authentication | `true` |
| `JWT_SECRET_KEY` | Token signing secret | a strong random string (see below) |
| `CORS_ORIGINS` | Allowed browser origins | your frontend URL(s), comma-separated |
| `DEFAULT_LLM_PROVIDER` | LLM backend | `openai` / `anthropic` / `together` / `ollama` |
| `OPENAI_API_KEY` (etc.) | Provider credentials | your key |
| `RATE_LIMIT_REQUESTS` | Requests per window per caller | tune to taste (default 120) |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window | `60` |
| `REDIS_URL` | Optional shared cache/limits | `redis://host:6379/0` |
| `METRICS_TOKEN` | Bearer token required to read `/metrics` | a random string (or empty to leave it open on a private network) |
| `API_RELOAD` | Auto-reload (dev only) | `false` |

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Note:** the app refuses to start when `REQUIRE_AUTH=true` and `JWT_SECRET_KEY`
> is unset, the shipped placeholder, or shorter than 32 bytes.

Settings changed at runtime through the Settings page (`POST /settings/update`)
are stored in the database (`app_settings` table), layered over the environment,
and picked up by every API instance within about 10 seconds. `.env` is never
rewritten, so the container filesystem can be read-only.

## 3. Database schema

The API container runs `scripts/migrate.py` on start, which applies any pending
migrations (and first stamps databases created by v1.0.0 containers, which had
no migration history). Set `SKIP_MIGRATIONS=1` if a separate job runs them.

Outside the container, run migrations against the production database before
first start:

```bash
alembic upgrade head
```

On future schema changes, generate and apply a migration:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## 4. Create an admin user

Registration creates regular users; the admin-only endpoints
(`/settings/data/clear`, `/settings/update`, …) require the `admin` role.
Register a user via the UI or `POST /auth/register`, then promote them:

```bash
python scripts/create_admin.py <username>
```

### Data ownership

With `REQUIRE_AUTH=true`, generated scenarios, game sessions, exercises,
webhooks and API keys belong to the user who created them. Other users get
`404` for them and never see them in listings; admins can see and manage
everything. The user who creates an exercise is its facilitator (only they can
start rounds, fire injects, pause, end, or read the full state), and players act
only as the team seat they joined with their own login.

Records created before this version, or while auth was off, have no owner and
are visible to admins only. To hand them to a user:

```bash
python scripts/assign_owner.py <username> --dry-run   # show what would change
python scripts/assign_owner.py <username>
```

## 5. Run

**API** (multiple workers behind a reverse proxy that terminates TLS):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

> **Redis is required for more than one worker or instance.** Without
> `REDIS_URL`, rate-limit counters live in each worker process, so four workers
> allow four times the configured limit. The API logs a warning at startup when
> it is running without shared counters.

**Frontend**:

```bash
streamlit run app/Home.py --server.port 8501
```

With `REQUIRE_AUTH=true`, users sign in on the UI's Login page; every page then
sends the token with its API calls and refreshes it when it expires.

### Docker Compose

`docker-compose.yml` brings up the API, frontend, PostgreSQL, and Redis wired
together (the API points at the bundled Postgres by default) with
`REQUIRE_AUTH=true`. It is safe by default:

- `POSTGRES_PASSWORD`, `REDIS_PASSWORD` and `JWT_SECRET_KEY` are required —
  `docker compose up` refuses to start until they are set in `.env`. Use
  URL-safe values (e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`),
  because the passwords are embedded in connection URLs.
- Only the API (8000) and UI (8501) are published. Postgres and Redis are
  reachable only on the internal compose network; Redis requires a password.
- `docker-compose.dev.yml` is a local-only override that publishes Postgres and
  Redis on `127.0.0.1` and enables hot reload. Never use it on a shared host.
- `docker-compose.monitoring.yml` adds Prometheus and Grafana, bound to
  `127.0.0.1` and requiring `GRAFANA_ADMIN_PASSWORD`.

Override `POSTGRES_DB` / `POSTGRES_USER` as needed. For production, prefer a
managed Postgres over the bundled container.

### Prebuilt container images

Each version tag publishes images to the GitHub Container Registry, so you can
pull instead of building:

```bash
docker pull ghcr.io/ap6pack/ai-tabletop-api:latest
docker pull ghcr.io/ap6pack/ai-tabletop-frontend:latest
```

Pin a release by version instead of `latest` (e.g. `:1.0.0`, `:1.0`, `:1`).

## 6. Health & scaling

- Health check: `GET /health` → `{"status": "healthy"}`.
- Metrics: `GET /metrics` serves Prometheus metrics (HTTP rates, latency,
  errors, LLM calls). Set `METRICS_TOKEN` to require a bearer token.
  `docker-compose.monitoring.yml` runs Prometheus and a provisioned Grafana
  dashboard. Counters are per process, so with `--workers N` each scrape sees
  one worker; prefer one worker per container when you need exact totals.
- The API is stateless — run N instances behind a load balancer; set `REDIS_URL`
  so rate limits and live-exercise state are shared across them.
- Back up PostgreSQL regularly; that is the system of record.

## 7. Migrating from the old file-based version

Earlier versions stored data as JSON files under `data/` and
`scenarios/generated/`. To import that data into the database:

```bash
alembic upgrade head            # ensure the schema exists
python scripts/import_legacy_data.py
```

The script is idempotent (it upserts by primary key) and reports how many
records it imported per store.
