# Changelog

All notable changes to the Cybersecurity War Gaming Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A provider test that runs the real Anthropic SDK against a local stub server, so SDK
  signature changes fail CI instead of production.
- `scripts/smoke_test_llm.py` makes one tiny real call per configured LLM provider, to
  check SDK upgrades that the (fully mocked) test suite cannot.
- The API container applies database migrations on start (`scripts/migrate.py`),
  stamping databases created by v1.0.0 containers first; `SKIP_MIGRATIONS=1`
  opts out.
- `GET /exercise/{id}/teams` lets an invited user list an exercise's teams (and
  see their own seat) before joining, without exposing game state.
- Tests: two-user isolation tests for every owned resource, exercise role tests,
  API flow tests for the game/scenarios/analytics/exercise routers, and AppTest
  runs of every page with `REQUIRE_AUTH=true` (logged in, logged out, expired
  token). Coverage of `api/` is 88%.
- **Community files** — `SECURITY.md` (private reporting via GitHub security advisories),
  `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), issue forms and a pull request template
  under `.github/`, `.github/dependabot.yml` (pip, GitHub Actions and Docker, weekly), and
  `.github/CODEOWNERS`.
- Tests: Streamlit AppTest smoke tests render every page against the in-process
  API and with the API down; new tests for the auth, library, LLM, MITRE and
  content-policy routers, the provider factory and Ollama/Together providers, the
  PDF/CSV report generator, the threat response engine, API keys, the audit chain
  and prompt injection. Coverage of `api/` rose from 68% to 84%.
- **Reproducible dependencies** — `requirements.in` / `requirements-dev.in` list the
  top-level packages; `requirements.txt` and `requirements-dev.txt` are fully pinned
  lock files generated with `uv pip compile --universal`. The Dockerfiles and CI
  install only from the lock files, and test tools (pytest, fakeredis, ruff, …) no
  longer ship in the production images.
- **CI tests Python 3.11, 3.12 and 3.13** (the range `pyproject.toml` declares) and
  runs `alembic upgrade head && alembic check` on SQLite and PostgreSQL.
- Scenario duration is read from the scenario's `metadata.duration_minutes`
  (set by `POST /scenarios/generate`'s new `duration_minutes` field) and drives the
  escalation timeline; 60 minutes remains the fallback.
- The API logs a startup warning when rate limiting runs without Redis, since each
  worker then counts separately; DEPLOY.md now lists Redis as required for more
  than one worker or instance.
- **Prometheus metrics** — `GET /metrics` exposes HTTP request counts, latency
  histograms, error counts, active requests, and LLM call counts/latency, so the
  bundled Prometheus scrape job and Grafana dashboard now receive data. Grafana
  gets its datasource and dashboard provisioned automatically. Optional
  `METRICS_TOKEN` protects the endpoint.
- `app_settings` table (Alembic migration `238cbfb8c9b4`) for runtime-edited settings.

### Security

- **Per-user data ownership** — game sessions, generated scenarios and exercises
  have an `owner_id` (migration `c0f41c4f1ff4`). With `REQUIRE_AUTH=true`, lists
  only show the caller's records and every per-record endpoint (game, scenarios,
  analytics/AAR/exports, ATT&CK coverage) returns 404 for someone else's; admins
  bypass. Webhooks and API keys are owned by the logged-in user (no more
  `user_id` from the request body, and webhook secrets are no longer returned).
  Library scenarios record their owner: private ones are hidden from others,
  only the owner can change visibility, and ratings count once per user.
  Records without an owner are admin-only; `scripts/assign_owner.py` hands them
  to a user.
- **Exercise roles come from the login** — the exercise's creator is its
  facilitator; `advance`, `inject`, `pause`, `end` and the full `/state` are
  facilitator-only (the `facilitator_id` query parameter is ignored). Players act
  only as the seat they joined (one seat per user per exercise); `team_id` /
  `member_id` in the body can no longer impersonate another team. Players only
  see their own team's view, team actions are visible to the acting team and the
  facilitator only, and `/poll` filters events the same way.
- **The Streamlit UI works with `REQUIRE_AUTH=true`** — every page sends the
  login token through `app/utils/api_client.py`, refreshes an expired access
  token once, and otherwise clears the login and asks the user to sign in again.
- **Prompt-injection hardening** — player actions, timeline entries and checked
  content are wrapped in a `<player_input>` block the system prompt marks as data;
  angle brackets and the reply markers the parsers look for (`STRUCTURED_DATA:`,
  `STATUS:` …) are defanged inside it. The game master's structured output is
  bounded (score change ±25, inventory ±1 on at most 3 tools, known event
  types/severities/actors only), the action filter and content-policy checks only
  trust a `STATUS:` line at the start of a line, and likely injection attempts
  are logged.
- **Audit logs moved to an append-only, hash-chained database table**
  (`audit_logs`, migration `b91650fa2a9e`). Entries survive restarts and are shared
  by all instances; each entry's hash covers the previous one, and the new
  admin-only `GET /audit/verify` reports modified, inserted or removed entries.
  On PostgreSQL a trigger refuses UPDATEs. `scripts/import_legacy_data.py`
  imports old `data/audit_logs/*.jsonl` files.
- **JWT secrets must be at least 32 bytes** when `REQUIRE_AUTH=true` (HS256 needs a
  key as long as its output); the test suite now signs with a 48-byte key.
- **The Settings API no longer rewrites `.env`.** Edited settings are stored in the
  database, survive restarts, are shared across instances, and values containing
  newlines or other control characters are rejected (previously a newline could
  inject extra settings into `.env`).
- **Webhook SSRF protection** — webhook URLs must be `https` and resolve only to
  public addresses; loopback, private, link-local (including cloud metadata at
  `169.254.169.254`) and reserved ranges are refused at registration, on update,
  and again right before each delivery. Redirects are no longer followed, and
  delivery runs on a background thread pool instead of blocking the request.
- **Audit endpoints are admin-only** — `/audit/logs`, `/audit/stats`,
  `/audit/compliance-report` and `POST /audit/cleanup` now require the `admin`
  role when `REQUIRE_AUTH=true`.
- **Safe `docker-compose.yml` defaults** — `REQUIRE_AUTH=true`; `POSTGRES_PASSWORD`,
  `REDIS_PASSWORD` and `JWT_SECRET_KEY` are required; Redis requires a password;
  only ports 8000 and 8501 are published. Database and Redis ports moved to
  `docker-compose.dev.yml` (bound to `127.0.0.1`), and Prometheus/Grafana moved
  to an opt-in `docker-compose.monitoring.yml` with a required Grafana password.

### Fixed

- Registering on the Login page reported failure even when the account was
  created (the page expected 200, the API returns 201).
- `/audit/compliance-report` and `/audit/logs` no longer fail with a 500 for
  date-only (naive) query parameters, and an inverted date range returns 400
  instead of 500.

### Changed

- Upgraded `anthropic` to 1.8.0. SDK 1.x removed the `temperature` argument from
  `messages.create()`; the Anthropic provider now sends it through `extra_body` for
  models that still honour it (older Claude models previously failed with a `TypeError`).
  Lock files regenerated with `uv`, restoring platform markers lost in Dependabot edits.
- `/audit/stats` now returns `total_entries` and the oldest/newest entry times, and
  `POST /audit/cleanup` reports `entries_deleted` (audit logs are no longer files).
- GitHub Actions moved to their Node 24 releases (`actions/checkout@v6`,
  `actions/setup-python@v6`, `actions/upload-artifact@v6`,
  `docker/setup-buildx-action@v4`, `docker/build-push-action@v7`,
  `docker/login-action@v4`, `docker/metadata-action@v6`).
- The test suite uses `httpx2` for Starlette's `TestClient`, removing the
  deprecation warning; the suite now runs warning-free.
- Default models updated to `claude-sonnet-5` (Anthropic) and `gpt-5.6-terra`
  (OpenAI). The providers omit `temperature` for models that reject it, send
  `max_completion_tokens` to OpenAI reasoning models, keep thinking off on Claude
  models where short replies matter, and read text blocks by type instead of
  assuming the first content block is text.
- `library_scenarios.rating` is declared as `Float` explicitly, so `alembic check`
  reports no drift on SQLAlchemy 2.1.
- `tests/test_audit_api.py` now runs in CI via `TestClient` instead of being
  skipped unless a live server was running.

## [1.0.0] - 2026-07-18

First public release — an open-source (Apache-2.0), AI-powered cybersecurity
war-gaming and tabletop-exercise platform. This is the first tagged/released
version; earlier `0.x` entries below document pre-release development milestones
(they were never tagged).

### Added

- **Scenario generation** — hierarchical, AI-generated organizations
  (departments, systems, vulnerabilities, threat actors) across 8 industries.
- **AI war-gaming** — an LLM "game master" runs interactive incident-response
  simulations with objectives, scoring, an incident timeline, and hints.
- **Multi-team exercises** — blue/red/white teams, round-based play, a crisis
  inject engine (sector templates, multiple trigger types), and facilitator controls.
- **Analytics & After-Action Review** — decision analysis, alternative-path
  suggestions, AAR generation, and PDF export.
- **MITRE ATT&CK integration** — 93 techniques across 14 tactics, wired into
  exercises and injects.
- **Compliance & executive reporting** — NIST CSF / PCI DSS / HIPAA scoring and
  an executive dashboard with financial-impact metrics.
- **Content safety** — four-tier content policy, pattern-based action filtering,
  post-generation validation, and hash-chained audit logging.
- **LLM providers** — OpenAI, Anthropic, Together AI, and Ollama behind a common
  provider abstraction.
- **Database storage layer (SQLAlchemy)** — users, sessions, exercises, API keys,
  webhooks, and scenarios persist to a database (SQLite by default, PostgreSQL
  for production via `DATABASE_URL`); Redis is an optional low-latency fast-path.
- **Alembic migrations** — schema managed with `alembic upgrade head`.
- **Rate limiting** — fixed-window limits (per authenticated user or client IP)
  on all API endpoints.
- **Deployment** — Dockerfiles and docker-compose (API, frontend, Postgres,
  Redis, monitoring), `DEPLOY.md`, and admin/legacy-import scripts.
- **CI** — lint, the test suite on both SQLite and PostgreSQL, and a Docker
  build; plus a security workflow (pip-audit, bandit, SBOM).

### Changed

- **Open-sourced under Apache-2.0** (previously proprietary); per-file SPDX
  headers, `NOTICE` file, copyright to Adam Rhys Heaton (Ap6pack) and contributors.
- **Storage moved from loose JSON files to a database** — indexed queries and
  transactional, concurrency-safe writes replace per-request directory scans.
- Documentation corrected to CI-verified reality.

### Removed

- The proprietary/commercial license and per-file proprietary headers.
- Stale phase-history docs, course transcripts, and committed runtime artifacts.

### Fixed

- **Boots without an API key** — LLM providers are constructed lazily, so the app
  imports and serves `/health` and the OpenAPI schema with no key configured.
- **Hermetic test suite** — an injected fake provider means no API key or network
  is required (269 passed, 1 skipped in a clean checkout).
- **Green CI** — fixed 1,368 `ruff` violations and applied the formatter, so the
  lint/test/build jobs actually run (both prior CI runs had failed at lint).
- Service bugs: inject-suggestion heuristics (dict vs. Pydantic model) and a
  stale game-state overwrite when completing objectives.

### Security

- **Authentication enforced** on product endpoints when `REQUIRE_AUTH=true`, with
  admin-only gating on destructive settings operations and a fail-fast guard
  against the default/empty `JWT_SECRET_KEY`.
- **Patched 23 known dependency vulnerabilities**; replaced the unmaintained
  `python-jose` (which pulled a no-fix-available `ecdsa`, PYSEC-2026-1325) with
  `PyJWT`.
- **Hardened CORS** — credentials are disabled with a wildcard origin; documented
  security headers (nosniff, frame-deny, CSP, HSTS, etc.).

---

## Pre-1.0 development history

_These milestones predate the first tagged release; they were not published as
versioned releases._

## [0.9.0] - 2026-02-19

### Added

#### Phase 9: Market Positioning - COMPLETE

**MITRE ATT&CK Integration**
- NEW: `MITREAttackService` with 93 techniques across 14 tactics
- Technique lookup, tactic filtering, and attack chain generation
- Integration with exercise and inject systems

**Multi-Team Exercise System**
- NEW: `ExerciseOrchestrator` with polling-based team coordination
- NEW: `ExerciseStore` for exercise state persistence
- Blue/Red/White team roles with distinct capabilities
- Round-based exercise progression
- NEW: Exercise Setup and Exercise Play UI pages

**Crisis Inject Engine**
- NEW: `InjectService` with 20 sector-specific templates
- 6 heuristic-based dynamic inject suggestions
- 5 trigger types: time, round, condition, event, manual
- Team response tracking and delivery management

**Executive Dashboard**
- NEW: `ExecutiveDashboardService` with Ponemon-calibrated financial metrics
- Industry-specific downtime cost calculations
- Risk scoring and trend analysis
- NEW: Executive Dashboard UI page

**Compliance Scoring**
- NEW: `ComplianceScoringService` for NIST CSF, PCI DSS, HIPAA
- Per-control scoring rubric with gap analysis
- Posture classification (Strong/Moderate/Developing/Weak)
- Multi-framework compliance reports

### Metrics
- 31 files, ~9,000 lines added
- 5 new services, 2 new routers, 3 new UI pages
- 45 new tests (112 total at this point)

---

## [0.8.0] - 2026-02-18

### Added

#### Phase 8: Deployment & Scaling - COMPLETE

**Docker Containerization**
- Dockerfile and docker-compose.yml for multi-service orchestration
- Health checks and resource limits
- Production-ready container configuration

**CI/CD Pipeline**
- GitHub Actions workflow for automated testing and deployment
- Linting, security scanning, and test stages
- Deployment pipeline with rollback procedures

**Monitoring & Observability**
- Application metrics and error tracking
- Performance monitoring configuration
- OpenTelemetry integration

**Security Hardening**
- JWT-based authentication with Argon2id password hashing
- Auth middleware and route protection
- API key management for external integrations
- Rate limiting and input validation
- Webhook service for event notifications

---

## [0.7.0] - 2026-02-17

### Added

#### Phase 7: Advanced Features - COMPLETE

**Analytics & After Action Review (Phase 6)**
- NEW: `DecisionAnalyzer` for decision quality scoring
- NEW: `AlternativePathService` for alternative path suggestions
- NEW: `AARService` for After Action Review generation
- NEW: `ReportGenerator` for PDF report export
- NEW: Analytics and After Action Review UI pages

**Advanced AI Features**
- NEW: `AdaptiveDifficultyService` for dynamic difficulty adjustment
- NEW: `TrainingPathService` for personalized training recommendations
- Player skill modeling and performance-based adaptation

**Authentication & Authorization**
- NEW: `AuthService` with JWT tokens and Argon2id password hashing
- NEW: Auth middleware for route protection
- Login page with session management

**Scenario Library**
- NEW: `ScenarioLibraryService` for pre-built scenario templates
- Scenario browsing, rating, and import/export
- NEW: Scenario Library UI page

**Integration Services**
- NEW: `WebhookService` for event notifications
- NEW: `APIKeyService` for external API key management

---

## [0.7.1] - 2025-11-05

### Changed

#### UI/UX Improvements
- Reorganized scenario loading workflow (moved to War Game sidebar)
- Improved UI messaging for scenarios vs sessions
- Enhanced Scenario Builder sidebar with recent scenarios

#### Bug Fixes
- Fixed session loading error handling in War Game page
- Fixed duplicate button key error in session loading
- Fixed game state validation logic
- Fixed page navigation references

---

## [0.7.0-beta] - 2025-11-05

### Added

#### Phase 5B: Enhanced Game Mechanics - COMPLETE

**Business Impact Calculations**
- NEW: `BusinessImpactService` (500 lines) - Industry-specific financial impact tracking
- Downtime rates: Financial ($500K/hr), Healthcare ($175K/hr), Technology ($120K/hr)
- System criticality multipliers, data loss costs, compliance penalties
- 12/12 tests passing

**Time Pressure Mechanics**
- NEW: `TimePressureService` (430 lines) - Countdown timers and automatic escalation
- Time-based scoring multipliers (Fast: 3x, Normal: 1x, Slow: 0.3x)
- Difficulty-scaled escalation checkpoints
- 10/10 tests passing

**Resource Constraints**
- NEW: `ResourceManager` (380 lines) - Action points, budget, staff management
- 15+ action types with varying costs
- Tool cooldowns and regeneration
- 12/12 tests passing

---

## [0.6.0] - 2025-11-04

### Added

#### Phase 4: Enhanced Safety & Policies - COMPLETE

- Pre-action content checking with 32 detection patterns (ActionFilterService)
- Post-generation validation (ContentValidatorService)
- Audit logging with SHA256 hashing and daily rotation (AuditLogService)
- Policy violation handling with automatic escalation (ViolationHandlerService)
- Compliance tracking and reporting
- Settings UI integration with audit viewer
- 47/47 tests passing

---

## [0.5.0] - 2025-11-04

### Added

#### Phase 5A: Core Game Mechanics - COMPLETE

- Automatic objective generation (ObjectiveGenerator, 6 types)
- System state tracking (SystemStateManager, 5 status types)
- Dynamic threat responses (ThreatResponseEngine, sophistication-based)
- 3 new real-time dashboards in War Game UI

---

## [0.4.0] - 2025-01-04

### Added

#### Phase 3.5: UI Integration & Code Quality

- Full UI integration: all pages wired to backend APIs
- Scenario Editor (6 tabs, 590 lines)
- Session Manager with load/save/delete
- Fully functional Settings page with .env persistence
- Professional logging system
- 5 critical bug fixes with root cause analysis
- Enterprise code quality: 0 debug prints, 0 bare excepts, 0 hardcoded URLs

---

## [0.3.0] - 2025-10-31

### Added

#### Phase 2 & 3: Scenario Generation + War Gaming

- Organization, Department, System, Vulnerability, Threat Actor generators
- Scenario Orchestrator with save/load workflow
- 8 industry templates
- AI Game Master with context-aware narrative generation
- Game session management with role-based inventory
- Scoring, objectives, incident timeline, hint system
- 14 API endpoints (6 scenarios + 8 game)

---

## [0.1.0] - 2025-10-31

### Added

#### Phase 1: Foundation

- FastAPI backend with OpenAPI docs
- LLM provider abstraction (OpenAI, Anthropic, Ollama)
- Content policy system (4 levels)
- Pydantic data models
- Streamlit multi-page frontend
- Configuration management

---

[1.0.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/releases/tag/v1.0.0
