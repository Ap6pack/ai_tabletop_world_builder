# Changelog

All notable changes to the Cybersecurity War Gaming Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Authentication is now enforced on product endpoints when `REQUIRE_AUTH=true`.**
  Previously the auth stack existed but no product router used it, so enabling
  the flag protected nothing. All product routers now require a valid bearer
  token when auth is enabled (the auth router stays open for register/login);
  with auth disabled (the dev default) behavior is unchanged.
- **Destructive/admin settings endpoints are gated behind an `admin` role.**
  `/settings/data/clear`, `/settings/update`, `/settings/reset/defaults`,
  `/settings/export`, and `/settings/provider/{provider}/key` now require an
  authenticated admin when auth is enabled (via a new `require_admin` dependency).
- **Patched 23 known dependency vulnerabilities** flagged by `pip-audit` (the
  Security workflow). Bumped `python-multipart`, `streamlit`/`pyarrow`,
  `requests`, `python-dotenv`, `pytest`/`pytest-asyncio`, and `fastapi`/`starlette`
  to fixed releases.
- **Replaced `python-jose` with `PyJWT`.** `python-jose` is effectively
  unmaintained and pulled in a vulnerable `ecdsa` (no-fix advisory
  PYSEC-2026-1325); PyJWT (HS256) removes that dependency entirely. Auth token
  encode/decode behavior is unchanged.

### Fixed

- **Boot without an API key**: services now construct their LLM provider lazily,
  so `from main import app` (and the health endpoint / OpenAPI schema) works with
  no key configured. Previously the API failed to import unless an OpenAI key was set.
- **Hermetic tests**: an autouse fixture injects a fake LLM provider, so the suite
  runs with no API key or network. In a clean checkout the suite is now 244 passed /
  1 skipped (previously 6 failed, 28 errors without a key).
- **CI lint**: fixed all 1,368 ruff violations and applied `ruff format`, so the CI
  `lint` job passes and the `test`/`build` jobs actually run (both prior CI runs on
  `main` had failed at lint and skipped everything downstream).

### Added

- **Database storage layer (SQLAlchemy)**: mutable application state — users,
  game sessions, exercises, API keys, and webhooks — now persists to a real
  database (SQLite by default, Postgres-ready via `DATABASE_URL`) instead of
  loose JSON files. Replaces O(n) directory scans with indexed queries and adds
  transactional, concurrency-safe writes. Redis remains an optional low-latency
  fast-path for live exercises; audit logs stay append-only JSONL by design.
- **Together AI provider**: implemented end-to-end (provider, factory, availability,
  settings API, request schema, and Settings UI). It was previously documented but
  unimplemented, raising `Unknown provider type` at runtime.
- **Auth security guard**: the app now refuses to start when `REQUIRE_AUTH=true` and
  `JWT_SECRET_KEY` is empty or the shipped placeholder. Auth/CORS env vars are now
  documented in `.env.example`.
- **AUDIT.md**: full project audit with findings, recommendations, and forward vision.

### Changed

- Stopped tracking runtime artifacts (`data/test_users/`, `data/audit_logs/`); added
  them to `.gitignore`.
- Corrected inflated status/metrics claims in README, PROJECT_SUMMARY, and CHANGELOG
  to CI-verified reality.

## [1.0.0] - 2026-02-20

### Added

#### Phase 10: Production Readiness - COMPLETE

**Integration Fixes**
- Added missing `pandas>=2.1.0` dependency to `requirements.txt`
- Updated `api/services/__init__.py` to export all 37 services (was only 11)
- Rebuilt `app/Home.py` navigation to link all 12 pages organized by category (Build/Play/Analyze/Admin)

**Shared Test Fixtures**
- NEW: `conftest.py` with reusable pytest fixtures for Organization, GameState, ExerciseState, ThreatActor, BusinessImpact, and more
- Eliminates duplicate model construction across test files

**New Test Suites (128 new tests across 8 files)**
- `test_inject_service.py` — 15 tests: template loading, inject creation, trigger evaluation, heuristic suggestions, response tracking
- `test_compliance_scoring_service.py` — 12 tests: framework loading, scoring rubric, gap analysis, posture labels
- `test_game_session_service.py` — 13 tests: session lifecycle, role-based inventory, file persistence, gameplay updates
- `test_scenario_orchestrator.py` — 8 tests: full pipeline, complexity counts, save/load, industry support
- `test_game_orchestrator.py` — 12 tests: game start, player actions, hints, end game, objectives
- `test_system_state_manager.py` — 12 tests: initialization, state updates, compromise/recovery, availability
- `test_generators.py` — 18 tests: all 6 generators (org, dept, system, vuln, threat, objective)
- `test_api_boot.py` — 5 tests: app import, health endpoint, router registration, OpenAPI schema

### Fixed

- **inject_service.py**: `suggest_inject()` heuristics never triggered because `business_impact` was treated as a dict but Pydantic v2 coerces it to a `BusinessImpact` model. Fixed to handle both types.
- **game_session_service.py**: `complete_objective()` had a stale-state bug where `update_score()` saved to disk but the in-memory `game_state` (with score=0) was saved over it. Fixed by saving objectives first, then calling update_score, then reloading from disk.

### Metrics
- **Test Suite**: 244 passed, 1 skipped (hermetic — no API key or network required)
- **Services Exported**: 37/37
- **API Routes**: 81 across 12 routers
- **UI Pages**: 12 (all navigable from Home)

---

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

## Version History

| Version | Phase | Description |
|---------|-------|-------------|
| 1.0.0 | Phase 10 | Production Readiness - full test coverage, integration fixes |
| 0.9.0 | Phase 9 | Market Positioning - ATT&CK, exercises, compliance |
| 0.8.0 | Phase 8 | Deployment & Scaling - Docker, CI/CD, monitoring |
| 0.7.0 | Phase 7 | Advanced Features - analytics, AAR, auth, AI adaptation |
| 0.6.0 | Phase 4 | Enhanced Safety & Policies |
| 0.5.0 | Phase 5A | Core Game Mechanics |
| 0.4.0 | Phase 3.5 | UI Integration & Code Quality |
| 0.3.0 | Phase 2-3 | Scenario Generation + War Gaming |
| 0.1.0 | Phase 1 | Foundation |

---

[1.0.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/Ap6pack/ai_tabletop_world_builder/compare/v0.7.0...v0.7.1
[0.3.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/releases/tag/v0.3.0
[0.1.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/releases/tag/v0.1.0
