# Deployment Guide

This guide covers deploying the Cybersecurity War Gaming Platform for a public,
multi-user environment. For local development see the README.

## Overview

- **API**: FastAPI (`main:app`), stateless — scale horizontally behind a load balancer.
- **Frontend**: Streamlit (`app/Home.py`).
- **Database**: PostgreSQL (required for production). All mutable state lives here.
- **Cache (optional)**: Redis — a low-latency fast-path for live multi-team
  exercises and shared rate-limit counters across instances.

## 1. Prerequisites

- Python 3.13
- A managed PostgreSQL database (RDS, Cloud SQL, Neon, Supabase, …)
- (Optional) Redis
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
| `API_RELOAD` | Auto-reload (dev only) | `false` |

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Note:** the app refuses to start when `REQUIRE_AUTH=true` and `JWT_SECRET_KEY`
> is unset or the shipped placeholder.

## 3. Database schema

Run migrations against the (empty) production database before first start:

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

## 5. Run

**API** (multiple workers behind a reverse proxy that terminates TLS):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Frontend**:

```bash
streamlit run app/Home.py --server.port 8501
```

> The Streamlit UI does not yet attach auth tokens. For a public deployment with
> `REQUIRE_AUTH=true`, either keep the UI on an internal network / behind an
> authenticating proxy, or expose only the API and build a token-aware client.

### Docker Compose

`docker-compose.yml` brings up the API, frontend, PostgreSQL, and Redis wired
together (the API points at the bundled Postgres by default). Override
`POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` as needed. For production,
prefer a managed Postgres over the bundled container.

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
