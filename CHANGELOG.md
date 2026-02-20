# Changelog

All notable changes to the Cybersecurity War Gaming Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- After Action Review system (Phase 6)
- Performance analytics and dashboards (Phase 6)
- Multi-user support (Phase 7)
- Advanced deployment features (Phase 8)

## [0.7.1] - 2025-11-05

### Changed

#### UI/UX Improvements
- **Reorganized scenario loading workflow** for better user experience
  - MOVED: Scenario loading from Scenario Builder to War Game page sidebar
  - Scenario Builder now focuses solely on creating scenarios
  - War Game page is now the central hub for loading and using scenarios
- **Improved UI messaging** to clarify scenarios vs. sessions
  - Updated "No active sessions" → "💡 No game sessions yet. Click '▶️ Start Incident' to create one!"
  - Added hint in Scenario Builder: "💡 Load scenarios from the War Game page sidebar"
  - Better guidance on the workflow: Load Scenario → Start Incident → Play Game
- **Enhanced Scenario Builder sidebar**
  - Shows count of saved scenarios
  - Displays recent 5 scenarios (read-only preview)
  - Clearer separation of concerns (create vs. use)

#### Bug Fixes
- Fixed session loading error handling in War Game page
  - More specific exception handling for network errors
  - Better error messages for different failure scenarios
- Fixed duplicate button key error in session loading
  - Changed from truncated session_id to full session_id for uniqueness
- Fixed game state validation logic
  - Added robust check for valid organization data
  - Filters out API error responses (checking for "detail" key)
  - Clears stale session state on load failures
- Fixed page navigation references
  - Updated all references from pages/3_* to pages/4_* (Session Manager)
  - Updated all references from pages/4_* to pages/5_* (Scenario Editor)

#### Files Modified
- `app/pages/2_War_Game.py` - Added scenario loading section to sidebar (~85 lines)
- `app/pages/1_Scenario_Builder.py` - Simplified sidebar to show scenario count only
- `app/Home.py` - Fixed page navigation reference

### Documentation
- Clarified distinction between **Scenarios** (templates/setups) and **Sessions** (active playthroughs)

## [0.7.0] - 2025-11-05

### Added

#### Phase 5B: Enhanced Game Mechanics - COMPLETE

**Feature 1: Business Impact Calculations**
- NEW: `BusinessImpactService` (500 lines) - Real-time financial impact tracking
  - Industry-specific downtime rates: Financial ($500K/hr), Healthcare ($175K/hr), Technology ($120K/hr), Retail ($72K/hr)
  - System criticality multipliers (1x-5x based on business importance)
  - Data loss costs by classification: Restricted ($500/record), Confidential ($250/record), Internal ($100/record), Public ($50/record)
  - Compliance penalty calculations for GDPR, HIPAA, PCI-DSS, SOX
  - Reputation damage with customer churn modeling
  - Impact event tracking with cumulative cost aggregation
  - Business impact dashboard in War Game UI (110 lines)
- Testing: 12/12 tests passing
- Files: `api/services/business_impact_service.py`, `test_business_impact.py`

**Feature 2: Time Pressure Mechanics**
- NEW: `TimePressureService` (430 lines) - Countdown timers and automatic escalation
  - Objective timers with expiry detection and auto-failure
  - Time-based scoring multipliers: Fast (<50% time): 3x, Normal (50-100%): 1x, Slow (>100%): 0.3x
  - Automatic threat escalation at difficulty-scaled intervals
    - Beginner: 2 escalation checkpoints (50%, 75%)
    - Intermediate: 4 checkpoints (33%, 66%)
    - Advanced: 6 checkpoints (25%, 50%, 75%)
    - Expert: 8 checkpoints (20%, 40%, 60%, 80%)
  - System degradation mechanics over time
  - Threat spreading mechanics for advanced scenarios
  - Timer & escalation dashboard with progress bars (100 lines UI)
- Testing: 10/10 tests passing
- Files: `api/services/time_pressure_service.py`, `test_time_pressure.py`

**Feature 3: Resource Constraints**
- NEW: `ResourceManager` (380 lines) - Strategic resource management system
  - Action points system scaled by difficulty:
    - Beginner: 15 AP, $150K budget, 7 staff
    - Intermediate: 10 AP, $100K budget, 5 staff
    - Advanced: 7 AP, $75K budget, 4 staff
    - Expert: 5 AP, $50K budget, 3 staff
  - Action cost system for 15+ action types:
    - Investigation: 1 AP, $0 (investigate, analyze, check logs)
    - Detection: 2 AP, $500 (scan systems)
    - Containment: 2-3 AP, $0-1K (isolate, block, quarantine)
    - Mitigation: 4-6 AP, $5K-25K (patch, restore, rebuild)
    - External Help: 2 AP, $50K-75K (vendor, consultant)
  - Tool cooldown management (5-60 minutes per tool)
  - Action point regeneration (0.25-0.75 pts/min based on difficulty)
  - Staff availability tracking
  - Affordability checking before every action
  - Resource management dashboard (150 lines UI)
- Testing: 12/12 tests passing
- Files: `api/services/resource_manager.py`, `test_resource_manager.py`

**Integration & UI**
- Updated `GameOrchestrator` with all three Phase 5B services
- Automatic business impact tracking on system downtime
- Timer creation for objectives with time limits
- Escalation rule generation based on scenario parameters
- Resource pool initialization and per-action management
- Three comprehensive UI dashboards in War_Game.py (360 lines total)
- All messages aggregated into game narrative

### Changed
- `api/services/game_orchestrator.py` - Integrated all Phase 5B services into game loop
- `app/pages/2_War_Game.py` - Added 3 new real-time dashboards (Business Impact, Timers, Resources)
- `api/models/schemas.py` - Added BusinessImpact, Timer, EscalationRule, ResourcePool, ActionCost models

### Metrics
- **New Code**: 3,730 lines (2,240 services + 1,130 tests + 360 UI)
- **Total Project**: ~11,500 lines of production code
- **Services**: 12 total (+3 from Phase 5B)
- **Real-Time Dashboards**: 6 total (+3 from Phase 5B)
- **Test Coverage**: 81/81 tests passing (100%)

## [0.6.0] - 2025-11-04

### Added

#### Phase 4: Enhanced Safety & Policies - COMPLETE

**Feature 1: Pre-Action Content Checking**
- NEW: `PatternMatcher` utility (230 lines) - 32 detection patterns across 4 categories
  - Credentials (12 patterns): API keys, passwords, tokens, AWS keys, private keys
  - PII (6 patterns): Emails, SSNs, phone numbers, credit cards
  - Exploit Code (11 patterns): SQL injection, XSS, RCE, directory traversal
  - Sensitive Info (3 patterns): IP addresses, internal paths, secrets
- NEW: `ActionFilterService` (280 lines) - Two-stage filtering system
  - Stage 1: Quick regex pattern matching (<100ms)
  - Stage 2: Optional LLM semantic analysis (2-4 seconds)
- Policy-aware blocking rules for 4 content policy levels
- Suggested alternatives for blocked actions
- Testing: 8/8 tests passing

**Feature 2: Post-Generation Validation**
- NEW: `ContentValidatorService` (380 lines) - Multi-type content validation
  - `validate_narrative()` - Game master responses
  - `validate_scenario()` - Complete scenarios
  - `validate_objective()` - Training objectives
  - `validate_hint()` - Contextual hints
- Auto-sanitization with 3 redaction styles (mask/remove/replace)
- Policy-aware content checking
- ValidationResult model with safety flags and violation details
- Testing: 8/8 tests passing

**Feature 3: Audit Logging System**
- NEW: `AuditLogService` (450 lines) - Comprehensive audit trail
  - Daily log rotation (audit_YYYY-MM-DD.jsonl)
  - SHA256 content hashing for privacy
  - JSONL format for efficient storage
  - Multi-dimensional filtering (date, type, severity, session, user)
  - Automatic log retention management (7-365 days configurable)
- 4 event types: policy_check, violation, filter, sanitization
- Compliance report generation with statistics
- Testing: 12/12 tests passing

**Feature 4: Policy Violation Handler**
- NEW: `ViolationHandlerService` (400 lines) - Automated violation responses
  - Severity-based responses (low/medium/high/critical)
  - Automatic escalation for repeat violations (24-hour window)
  - Educational content generation (violation-specific)
  - Alternative suggestions for safe approaches
- Violation metrics tracking (total, by severity, by type)
- ViolationResponse model with action, message, educational content
- Testing: 12/12 tests passing

**Feature 5: Compliance Tracking**
- ComplianceReport model with comprehensive metrics
  - Total checks and violations
  - Violation rate calculation
  - Violations by type and severity
  - Policy level distribution
  - Top violation patterns
- Automated report generation for any date range
- Integrated with audit logging service

**Feature 6: Content Filtering** (Combined Features 1-3)
- Unified filtering across action filter and content validator
- 4 filter categories with 32 patterns
- 3 redaction styles (mask/remove/replace)
- Policy-aware filtering for all content types

**Feature 7: Settings UI Integration**
- NEW: `api/routers/audit.py` (200 lines) - Audit API endpoints
  - `GET /audit/logs` - Retrieve logs with filters
  - `GET /audit/compliance-report` - Generate compliance reports
  - `POST /audit/cleanup` - Clean up old logs
  - `GET /audit/stats` - Get audit statistics
- Enhanced Settings UI in `app/pages/3_Settings.py` (+408 lines):
  - Content Policy & Safety Configuration (222 lines)
    - Content filtering toggles
    - Filter category checkboxes
    - Redaction style selector
    - Audit logging settings
    - Violation handling configuration
  - Audit Log Viewer (68 lines)
    - Filter by event type, severity
    - Formatted table display
    - Load on demand
  - Compliance Reporting (118 lines)
    - Date range picker
    - Format selector (JSON/CSV)
    - Metrics display (checks, violations, rate, risk level)
    - Detailed breakdowns (by type, severity, patterns)
    - Export functionality
- Save settings integration (11 new fields persist to .env)
- Testing: 7/7 API tests passing

### Technical Details

**Code Statistics**
- Total new code: ~2,300 lines
- Services created: 4 major services + 1 utility
- API endpoints: 4 new endpoints
- UI components: 3 major sections (408 lines)
- Test files: 5 comprehensive suites
- Test coverage: 47/47 tests passing (100%)

**Models Added** (7 Pydantic models)
- ActionCheckResult - Pre-action filtering results
- ValidationResult - Post-generation validation results
- AuditLog - Audit log entry
- PolicyViolation - Violation record
- ViolationResponse - Violation handling response
- ComplianceReport - Compliance reporting
- FilterConfig - Content filter configuration

**Files Created** (11 new files)
1. `api/utils/pattern_matcher.py` (230 lines)
2. `api/services/action_filter_service.py` (280 lines)
3. `api/services/content_validator_service.py` (380 lines)
4. `api/services/audit_log_service.py` (450 lines)
5. `api/services/violation_handler_service.py` (400 lines)
6. `api/routers/audit.py` (200 lines)
7. `test_action_filter.py` (130 lines)
8. `test_content_validator.py` (150 lines)
9. `test_audit_log.py` (280 lines)
10. `test_violation_handler.py` (250 lines)
11. `test_audit_api.py` (180 lines)

**Files Modified** (5 files)
1. `api/models/schemas.py` - Added 7 Phase 4 models, added uuid import
2. `api/models/__init__.py` - Exported 7 new models
3. `app/pages/3_Settings.py` - Added 408 lines for Phase 4 UI
4. `main.py` - Registered audit router
5. `api/routers/__init__.py` - Exported audit_router

**Performance**
- Pattern matching: <100ms (regex-based)
- LLM semantic check: 2-4 seconds (optional)
- Audit log write: <10ms
- Audit log retrieval: <100ms for 1000 entries
- Compliance report: <500ms for 10,000 logs

### Documentation

- NEW: `PHASE4_COMPLETE.md` - Comprehensive Phase 4 completion document
- Updated `ROADMAP.md` - Marked Phase 4 complete, updated timeline
- Updated `PROJECT_SUMMARY.md` - Status and metrics
- Updated `CHANGELOG.md` - This v0.6.0 entry

### Metrics

- **Lines of Code**: ~7,800+ total production code (+2,300 this release)
- **API Endpoints**: 24 total (+4 this release: 4 audit endpoints)
- **Services**: 9 total (+4 this release: action filter, content validator, audit log, violation handler)
- **Files Created**: 11 (Phase 4 services, utilities, tests)
- **Files Modified**: 5 (Models, Settings UI, API registration)
- **Test Coverage**: 47/47 tests passing (100% pass rate)

### Security & Privacy

- SHA256 content hashing (no plaintext storage)
- PII redaction and credential filtering
- JSONL audit log format (industry standard)
- Configurable retention policies (7-365 days)
- Compliance reports for regulatory requirements
- Tamper-evident audit trail

### Configuration

**New Environment Variables** (11 settings):
- `ENABLE_ACTION_FILTERING` - Pre-action content filtering toggle
- `ENABLE_CONTENT_VALIDATION` - Post-generation validation toggle
- `ENABLE_AUDIT_LOGGING` - Audit logging toggle
- `ENABLE_CREDENTIAL_DETECTION` - Credential detection toggle
- `ENABLE_PII_DETECTION` - PII detection toggle
- `ENABLE_EXPLOIT_DETECTION` - Exploit code detection toggle
- `ENABLE_SENSITIVE_DETECTION` - Sensitive info detection toggle
- `REDACTION_STYLE` - Redaction style (mask/remove/replace)
- `AUDIT_RETENTION_DAYS` - Log retention period (7-365)
- `VIOLATION_ESCALATION_THRESHOLD` - Escalation threshold (1-5)
- `VIOLATION_TIME_WINDOW` - Time window for repeat violations (1-72 hours)

## [0.5.0] - 2025-11-04

### Added

#### Phase 5A: Core Game Mechanics - COMPLETE

**Feature 1: Automatic Objective Generation**
- NEW: `ObjectiveGenerator` service (380 lines) - Intelligently generates training objectives
- NEW: `Objective` model with structured fields (type, success_criteria, hints, time_limits, points)
- 6 objective types: detect, contain, mitigate, investigate, protect, report
- Contextual generation based on scenario vulnerabilities, threats, and systems
- Difficulty-appropriate point values (15-50 points)
- Enhanced War Game UI with objective dashboard
  - Type-specific icons (🔍 🛡️ 🔧 🔬 🔐 📝)
  - Difficulty badges (🟢 🟡 🔴)
  - Status grouping (in-progress, pending, completed, failed)

**Feature 2: System State Modifications**
- NEW: `SystemStateManager` service (330 lines) - Real-time system health tracking
- NEW: `SystemState` model with status and health fields
- 5 status types: online, offline, compromised, recovering, patched
- Health tracking (0-100%) with severity-based damage
- Automatic initialization of all systems on game start
- System status dashboard in War Game UI (100+ lines)
  - Visual summary metrics (🟢 Online, 🟡 At Risk, 🔴 Offline)
  - Priority-based display (compromised first)
  - Criticality badges (🔥 critical, ⚠️ high, 📌 medium)
  - Real-time health percentages

**Feature 3: Dynamic Threat Responses**
- NEW: `ThreatResponseEngine` service (400 lines) - Simulates intelligent threat behavior
- NEW: `ThreatActorState` model with detection/aggression tracking
- Sophistication-based initial aggression (nation-state: 85%, organized-crime: 70%, hacktivist: 50%)
- Dynamic responses to player actions:
  - Detection actions increase detection level (10-25%)
  - Containment actions: 60% success, 40% escalation
  - Mitigation actions remove compromised systems (40% per system)
- Automatic escalation mechanics:
  - Aggression increases 10-20% over time
  - 50% chance to compromise new systems
- Evasion behavior when highly detected (>60%)
  - 30% chance to go dormant if detection >80%
- Threat status dashboard in War Game UI (115+ lines)
  - Status summary (🔴 Active, 🟡 Contained, 🔵 Dormant, 🟢 Eliminated)
  - Sophistication badges and aggression meters
  - Current tactics and compromised system counts

### Technical Details
- Added 3 new Pydantic models: Objective, SystemState, ThreatActorState
- Created 3 new services: ~1,110 lines of game logic
- Enhanced GameState model with objectives, system_states, threat_states fields
- Updated Game Orchestrator to initialize all mechanics on game start
- Added ~285 lines of UI components across 3 dashboards
- All features fully tested and working end-to-end

## [0.4.0] - 2025-01-04

### Added

#### Phase 3.5: UI Integration & Code Quality

**UI Integration - Complete End-to-End Functionality**
- Connected Scenario Builder to `/scenarios/generate` API with proper error handling
- **NEW: Scenario Editor** (`4_Scenario_Editor.py` - 590 lines)
  - 6 tabs: Organization, Departments, Systems, Vulnerabilities, Threat Actors, Game Objectives
  - Full CRUD operations on all scenario elements
  - Deep copy pattern to preserve originals
  - Revert changes functionality
  - 8 suggested objectives for quick setup
- Connected War Game to all `/game/*` endpoints
- **NEW: Session Manager** (`3_Session_Manager.py`)
  - List sessions with filtering (all/in-progress/completed/failed)
  - Load and resume saved sessions
  - Delete sessions (including active ones)
- **NEW: Fully Functional Settings Page**
  - Save settings to `.env` file (persistent)
  - Real-time storage statistics
  - Export configuration as JSON
  - Clear all data with confirmation
  - Reset to defaults while preserving API keys
  - Test LLM connection with user credentials

**Settings API** (`api/routers/settings.py` - 310 lines)
- `GET /settings/current` - Get current configuration
- `POST /settings/update` - Update and persist to .env
- `GET /settings/storage/stats` - Real-time storage metrics
- `POST /settings/export` - Export config as JSON
- `DELETE /settings/data/clear` - Delete all scenarios/sessions
- `POST /settings/reset/defaults` - Reset configuration

**Configuration Management**
- **NEW: Frontend Config** (`app/config.py`)
  - Centralized API_BASE_URL configuration
  - Environment-based host/port settings
  - Standardized timeout constants (DEFAULT_TIMEOUT, HEALTH_CHECK_TIMEOUT, LONG_OPERATION_TIMEOUT)
- **NEW: Constants Mapping** (`app/constants.py`)
  - UI ↔ API value mappings for player roles, scenario types, etc.
  - Single source of truth for dropdown values

**Professional Logging System**
- **NEW: Logger Utility** (`api/utils/logger.py`)
  - Structured logging with timestamps
  - File and console handlers
  - Separate log files per module
  - Proper log levels (INFO, DEBUG, WARNING, ERROR)

**Documentation**
- **NEW: Scenario Editor Guide** (`app/SCENARIO_EDITOR.md`)
- **NEW: Phase Completion Doc** (`UI_INTEGRATION_AND_QUALITY_COMPLETE.md`)

### Fixed

#### Critical Bug Fixes

**Bug #1: Player Role Validation Error**
- Fixed: "literal_error" when starting games with "mixed-team" role
- Root cause: String manipulation produced "mixed-team" but backend expected "mixed"
- Solution: Created `constants.py` with proper UI → API mappings
- Files: `app/constants.py` (NEW), `app/pages/1_Scenario_Builder.py`, `app/pages/2_War_Game.py`

**Bug #2: Session Loading Display Issue**
- Fixed: "No scenario loaded" shown after successfully loading session
- Root cause: Only checked `active_scenario`, missed `game_state`
- Solution: Check both sources for scenario data
- File: `app/pages/2_War_Game.py`

**Bug #3: Cannot Delete Active Sessions**
- Fixed: Delete button only appeared for completed/failed sessions
- Root cause: Missing DELETE endpoint + UI restriction
- Solution: Added `DELETE /game/sessions/{session_id}` endpoint
- Files: `api/routers/game.py`, `api/services/game_orchestrator.py`, `api/services/game_session_service.py`

**Bug #4: Scenario Editor Changes Not Persisting**
- Fixed: All edits lost on page rerun
- Root cause: Local list updates never saved to `st.session_state`
- Solution: Update session state after every modification
- File: `app/pages/4_Scenario_Editor.py`

**Bug #5: Settings Page Showing Fake Success**
- Fixed: Test Connection always succeeded even with invalid keys
- Root cause: TODO comment with fake `st.success()` call
- Solution: Implement actual API test calling `/llm/complete`
- File: `app/pages/3_Settings.py`

### Changed

#### Professional Code Cleanup

**Removed Debug Code**
- Eliminated all 11 `print()` statements from production code
- Replaced with proper `logger.info()`, `logger.debug()`, `logger.error()` calls
- Files: `api/services/scenario_orchestrator.py`, `api/routers/game.py`, `api/routers/scenarios.py`

**Fixed Exception Handling**
- Replaced all 10 bare `except:` clauses with specific exception types
- Used `requests.exceptions.RequestException`, `requests.exceptions.Timeout`, etc.
- Added proper error logging with context
- Files: `app/Home.py`, all pages in `app/pages/`, `app/utils/api_client.py`

**Centralized Configuration**
- Removed 19 instances of hardcoded `http://127.0.0.1:8000`
- Replaced with `API_BASE_URL` from `app/config.py`
- Replaced hardcoded timeouts with named constants
- Files: All frontend files

**Consistent Error Messages**
- User-friendly error messages in UI
- Detailed error logging in backend
- No stack traces exposed to end users
- Full tracebacks logged to files for debugging

### Documentation

- Updated README.md with v0.4.0 features
- Updated ROADMAP.md with Phase 3.5 completion
- Added UI_INTEGRATION_AND_QUALITY_COMPLETE.md
- Added app/SCENARIO_EDITOR.md

### Metrics

- **Lines of Code**: ~4,400 total production code (+2,000 this release)
- **API Endpoints**: 20 total (+7 this release: 1 game DELETE, 6 settings)
- **Files Created**: 7 (Scenario Editor, Config, Constants, Logger, Settings API, Docs)
- **Files Modified**: 12 (Backend routers/services, All frontend pages)
- **Bugs Fixed**: 5 critical bugs with root cause analysis
- **Code Quality**: 0 debug prints, 0 bare excepts, 0 hardcoded URLs

## [0.3.0] - 2025-10-31

### Added

#### Phase 3: Interactive War Gaming

**Game Session Management** (`game_session_service.py` - 270 lines)
- Complete game session lifecycle management
- Role-based starting inventory system for 4 player roles:
  - SOC Analyst (SIEM, IDS/IPS, Log Analysis Tools)
  - Incident Responder (EDR, Forensics, Network Analyzer)
  - Security Engineer (Firewall, Vulnerability Scanner, Config Mgmt)
  - CISO (Executive Dashboard, Risk Management Tools)
- Tool inventory tracking with usage counts
- Access level management (user, admin, siem, network, executive)
- Credential acquisition and tracking
- Real-time scoring system with reasons
- Time tracking (minutes elapsed)
- Incident timeline with event types (detection, action, consequence, escalation)
- Objective completion tracking
- Session persistence to disk (JSON format)
- Session status management (in-progress, completed, failed)

**AI Game Master Service** (`game_master_service.py` - 320 lines)
- Dynamic narrative generation based on player actions
- Context-aware AI responses using game state
- Role-appropriate challenge generation
- Realistic constraint enforcement (tools, access levels)
- Action validation and consequence simulation
- Discovery system for uncovering information
- Inventory change recommendations
- Score calculation with reasoning
- Event generation for timeline
- Hint generation system
- Educational guidance with realistic scenarios
- Threat actor behavior simulation
- Structured data extraction from LLM responses

**Game Orchestrator** (`game_orchestrator.py` - 200 lines)
- Coordination between session management and AI game master
- `start_new_game()` - Initialize session and generate opening narrative
- `process_player_action()` - Handle action, update state, return response
- `get_hint()` - Generate contextual hints for players
- `end_game()` - Finalize session with status
- `complete_objective()` - Track objective completion
- `get_session_state()` - Retrieve current game state
- `list_sessions()` - List all sessions with filtering

**Game API Router** (`game.py` - 200 lines)
- `POST /game/start` - Start new war gaming session
- `POST /game/action` - Process player action
- `GET /game/state/{session_id}` - Get current game state
- `POST /game/hint` - Request contextual hint
- `POST /game/end` - End game session
- `GET /game/sessions` - List all sessions with optional status filter
- `POST /game/objective` - Mark objective as completed/failed
- Complete request/response models with validation

**Testing and Documentation**
- `test_war_game.sh` - Comprehensive test script for war gaming
- `PHASE3_COMPLETE.md` - Complete Phase 3 documentation
- Full integration testing with real scenarios

**Storage**
- `data/sessions/` directory for session persistence
- JSON-based session storage with full game state
- Automatic save on state changes

#### Phase 2: Scenario Generation

**Organization Generator** (`organization_generator.py` - 370 lines)
- Generate realistic organizations across 8 industries:
  - Financial Services
  - Healthcare
  - Technology
  - Manufacturing
  - Retail & E-commerce
  - Education
  - Government
  - Energy & Utilities
- Industry-specific templates with compliance frameworks
- Organization size configuration (small, medium, large, enterprise)
- Security posture generation (developing, mature, advanced)
- Complete business context generation

**Department Generator** (`department_generator.py` - 120 lines)
- Business department generation with functions
- Data classification (public, internal, confidential, restricted)
- Compliance requirements per department
- Industry-appropriate department structures
- Configurable number of departments (1-10)

**System Generator** (`system_generator.py` - 150 lines)
- IT asset generation (servers, workstations, network devices, applications, databases)
- Operating system selection (Windows, Linux, macOS, cloud)
- Service and port configuration
- Security control assignment (firewall, antivirus, encryption, IDS/IPS, etc.)
- Criticality assessment (low, medium, high, critical)
- 2-5 systems per department

**Vulnerability Generator** (`vulnerability_generator.py` - 170 lines)
- CVE-based vulnerability generation
- Severity ratings (low, medium, high, critical)
- Exploitation complexity assessment
- System-specific vulnerabilities
- Remediation guidance
- Affected systems tracking
- Both known CVEs and configuration issues

**Threat Actor Generator** (`threat_actor_generator.py` - 160 lines)
- Threat actor profile generation
- Motivation types (financial, espionage, ideology, disruption)
- Sophistication levels (script-kiddie, organized-crime, nation-state, insider)
- MITRE ATT&CK TTP mapping:
  - Initial Access techniques
  - Execution methods
  - Persistence mechanisms
  - Defense Evasion
  - Credential Access
  - Impact tactics
- Target identification
- 1-3 threat actors per organization

**Scenario Orchestrator** (`scenario_orchestrator.py` - 240 lines)
- Complete scenario generation workflow
- Hierarchical generation (Org → Depts → Systems → Vulns → Threats)
- Progress tracking and status updates
- Scenario validation
- Save/load functionality with JSON
- List and manage saved scenarios
- Industry information retrieval
- Complexity configuration

**Scenarios API Router** (`scenarios.py` - 180 lines)
- `POST /scenarios/generate` - Generate complete scenario
- `GET /scenarios/industries` - List supported industries
- `GET /scenarios/industries/{industry}` - Get industry details
- `GET /scenarios/list` - List all saved scenarios
- `GET /scenarios/{filename}` - Load scenario by filename
- `DELETE /scenarios/{filename}` - Delete saved scenario
- Complete request/response models

**Testing and Documentation**
- `test_scenario_generation.sh` - Test script for scenario generation
- `PHASE2_COMPLETE.md` - Complete Phase 2 documentation
- Comprehensive API testing

**Storage**
- `scenarios/generated/` directory for saved scenarios
- JSON-based scenario files with timestamps
- Automatic filename generation from organization name

### Changed

#### API Updates
- Updated main.py to include scenarios and game routers
- Updated `api/routers/__init__.py` to export new routers
- Updated `api/services/__init__.py` to export new services
- Enhanced data models with game state and inventory

#### Bug Fixes
- Fixed LLM provider factory None handling in `api/providers/factory.py`
- Changed from `or` operator to explicit `if model is None` checking
- Fixed OpenAPI schema examples to avoid "string" placeholder errors

#### Documentation Updates
- README.md API section updated with actual endpoints
- Removed "coming soon" placeholders for implemented features
- Added phase completion documentation

### Technical Details

#### Code Statistics
- **Phase 2**: ~1,400 lines of scenario generation code
- **Phase 3**: ~990 lines of war gaming code
- **Total new code**: ~2,400 lines
- **New API endpoints**: 14 endpoints (6 scenarios + 8 game)
- **New services**: 9 major services
- **Test coverage**: 3 test scripts with comprehensive scenarios

#### Performance
- Scenario generation: 30-60 seconds (depends on complexity)
- Game start: 3-5 seconds (LLM generation)
- Player action: 2-4 seconds (LLM generation)
- Game state retrieval: <100ms (file read)
- Hint generation: 1-2 seconds (LLM generation)

#### Architecture
- Hierarchical generation pipeline
- Async/await throughout
- JSON-based persistence
- Session isolation
- Stateless API design

### Notes

#### What Works
- ✅ Complete scenario generation (Phase 2)
- ✅ Interactive war gaming (Phase 3)
- ✅ AI-powered game master
- ✅ Role-based inventory system
- ✅ Dynamic narrative generation
- ✅ Scoring and objectives
- ✅ Session management
- ✅ Hint system
- ✅ All API endpoints functional
- ✅ Comprehensive testing

#### What's Next (Phase 4-5)
- 🚧 Enhanced game mechanics (time pressure, resource limits)
- 🚧 Automatic objective generation
- 🚧 After Action Review (AAR) generation
- 🚧 Performance analytics dashboard
- 🚧 Decision tree visualization
- 🚧 Multi-player support

## [0.1.0] - 2025-10-31

### Added

#### Project Foundation
- Initial project structure and architecture
- Complete directory organization (api/, app/, config/, scenarios/, data/)
- Python package structure with proper `__init__.py` files
- `.gitignore` for Python, virtual environments, and sensitive data

#### Backend (FastAPI)
- FastAPI application entry point (`main.py`)
- Complete API architecture with modular design
- OpenAPI documentation at `/docs` endpoint
- Health check endpoint at `/health`
- CORS middleware configuration

#### LLM Provider System
- Abstract base provider interface (`BaseLLMProvider`)
- OpenAI GPT provider implementation (GPT-4, GPT-3.5)
- Anthropic Claude provider implementation (Claude 3.5 Sonnet, Opus)
- Ollama local model provider implementation (Llama 3, Mistral)
- Provider factory with automatic health checking
- Flexible provider configuration via environment variables
- Support for provider-specific parameters (temperature, max_tokens)

#### Data Models (Pydantic)
- `Organization` model with industry and security posture
- `Department` model with business functions and data classification
- `System` model for IT assets (servers, workstations, applications, etc.)
- `Vulnerability` model with CVE IDs and severity ratings
- `ThreatActor` model with sophistication levels and TTPs
- `GameState` model for war gaming sessions
- `Inventory` model for tools and access levels
- `IncidentEvent` model for timeline tracking
- `Tool` model for security tools (SIEM, EDR, IDS, etc.)
- Request/response models for all API endpoints

#### Content Policy System
- Four-tier content policy framework:
  - **Defensive**: Security monitoring and controls only
  - **Educational**: Realistic scenarios with defensive focus (default)
  - **Advanced**: Red team tactics for experienced professionals
  - **Unrestricted**: Full realism for expert training
- AI-powered content safety checking
- Configurable policy enforcement per session
- Detailed policy descriptions with allowed/blocked categories
- Content check API endpoint (`/content-policy/check`)
- Policy listing endpoint (`/content-policy/policies`)

#### API Services
- `LLMService` for managing LLM completions
- `ContentPolicyService` for safety and moderation
- Service-level business logic abstraction
- Async/await support throughout

#### API Routers
- `/llm/complete` - Generate LLM completions
- `/llm/providers` - Check provider availability
- `/content-policy/check` - Verify content safety
- `/content-policy/policies` - List available policies

#### Frontend (Streamlit)
- Multi-page Streamlit application structure
- **Home Page**: Platform overview and quick navigation
- **Scenario Builder Page**: Scenario configuration interface
  - Industry selection (8 sectors)
  - Organization size options
  - Complexity and difficulty settings
  - Focus area selection (10+ threat types)
  - Player role selection
  - Learning objectives input
  - Scenario preview (placeholder)
- **War Game Page**: Interactive incident response interface
  - Chat-based interaction system
  - Incident timeline display
  - Tool inventory sidebar
  - Objective tracking
  - Game controls (start, pause, end)
  - Hint system
- **Settings Page**: Platform configuration
  - LLM provider selection and configuration
  - API key management
  - Content policy level selection
  - Session configuration options
  - Storage settings
  - System status display

#### Configuration System
- Environment-based configuration using `pydantic-settings`
- `.env.example` template with all options
- Settings class with type validation
- Support for multiple LLM providers
- Configurable content policies
- Session and storage path settings
- API server configuration (host, port, reload)

#### Documentation
- Comprehensive `README.md` with:
  - Project overview and architecture
  - Feature descriptions
  - Installation instructions
  - Usage guide
  - API documentation
  - Content policy details
  - Troubleshooting guide
- `QUICKSTART.md` for rapid setup:
  - 5-minute quick start guide
  - First war game walkthrough
  - Example session scenarios
  - Training path recommendations
  - Common troubleshooting steps
- `ROADMAP.md` with development plan:
  - 8 development phases outlined
  - Task breakdowns per phase
  - Time estimates (5-6 months total)
  - Success metrics defined
  - Contributing guidelines
- `CHANGELOG.md` (this file)

#### Dependencies
- FastAPI 0.109.0 for REST API
- Uvicorn 0.27.0 for ASGI server
- Streamlit 1.31.0 for web UI
- Pydantic 2.5.3 for data validation
- OpenAI 1.10.0 for GPT models
- Anthropic 0.18.1 for Claude models
- HTTPX 0.26.0 for HTTP client (Ollama)
- Python-dotenv 1.0.0 for environment variables
- Pytest 7.4.4 for testing

#### Storage Structure
- `scenarios/generated/` for saved scenarios
- `data/` for application data
- `.gitkeep` files to preserve empty directories

#### Developer Tools
- Test structure with pytest support
- Utilities module for shared functions
- Type hints throughout codebase
- Async/await patterns for scalability

### Changed
- Adapted fantasy RPG framework to cybersecurity training context
- Replaced "Together AI" with flexible multi-provider system
- Replaced "Gradio" with Streamlit for better dashboard capabilities
- Modified content policies from single "defensive" to four-tier system
- Updated data models from fantasy (kingdoms, NPCs) to security (organizations, systems, threats)

### Technical Details

#### Architecture Decisions
- **Backend**: FastAPI chosen for async support, OpenAPI docs, and performance
- **Frontend**: Streamlit chosen for rapid UI development and dashboard capabilities
- **LLM Abstraction**: Provider pattern for easy switching between OpenAI, Anthropic, Ollama
- **Data Format**: JSON for scenarios, Pydantic for validation
- **Configuration**: Environment variables for security and flexibility

#### Code Organization
```
api/
├── models/         # Data schemas and validation
├── providers/      # LLM provider implementations
├── services/       # Business logic layer
└── routers/        # API endpoint handlers

app/
├── Home.py         # Main dashboard
└── pages/          # Multi-page application

config/             # Settings and configuration
scenarios/          # Generated training scenarios
data/               # Application data storage
```

#### Security Considerations
- API keys stored in `.env` (not version controlled)
- Content policy system prevents malicious content
- Input validation via Pydantic models
- CORS configuration for API access control
- Four-tier content policy system for appropriate training levels

### Notes

This release establishes the complete foundation for the platform. The core generation and game mechanics (Phases 2-3) are next in the development roadmap.

#### What Works
- ✅ Project structure complete
- ✅ API skeleton with documentation
- ✅ LLM provider abstraction functional
- ✅ Content policy system operational
- ✅ UI pages created with navigation
- ✅ Configuration system working
- ✅ Documentation comprehensive

#### What's Next (Phase 2)
- 🚧 Implement hierarchical scenario generator
- 🚧 Create organization/department/system generation
- 🚧 Add vulnerability and threat actor generation
- 🚧 Wire up Scenario Builder to backend API
- 🚧 Enable scenario save/load functionality

---

## Version History

### Version Numbering
- **0.1.0** - Initial foundation and architecture
- **0.2.0** - (Skipped - merged into 0.3.0)
- **0.3.0** - Scenario generation (Phase 2) + Interactive war gaming (Phase 3)
- **0.4.0** - Planned: Enhanced safety and analytics (Phases 4-6)
- **1.0.0** - Planned: Production-ready release (Phases 7-8)

---

## Migration Notes

### From Fantasy RPG to Cybersecurity Training

This project adapts the AI-powered text-based RPG framework for cybersecurity training:

| Fantasy RPG | Cybersecurity Platform |
|-------------|------------------------|
| Worlds | Organizations |
| Kingdoms | Departments |
| Towns | Systems/Networks |
| NPCs | Assets/Vulnerabilities |
| Monster Encounters | Security Incidents |
| Combat | Incident Response |
| Inventory (swords, potions) | Tools (SIEM, EDR, forensics) |
| Character Classes | Security Roles |
| Game Master | AI Threat Simulator |

### Course Materials Reference

Original course materials preserved in `context/` directory:
- L1: Hierarchical Content Generation → Scenario Generation
- L2: Interactive RPG → War Gaming
- L3: Content Moderation → Safety Policies
- L4: JSON Game Mechanics → Tool/Inventory System

---

**Legend**:
- ✅ Complete
- 🚧 In Progress
- 📝 Planned
- 🔮 Future

[Unreleased]: https://github.com/Ap6pack/ai_tabletop_world_builder/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/releases/tag/v0.3.0
[0.1.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/releases/tag/v0.1.0
