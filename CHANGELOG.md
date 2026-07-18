# Changelog

All notable changes to the Cybersecurity War Gaming Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
