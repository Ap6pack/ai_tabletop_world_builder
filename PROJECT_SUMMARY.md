# Cybersecurity War Gaming Platform - Project Summary

## Project Status

**Version**: 1.0.0
**Status**: Phase 10 Production Readiness Complete
**License**: Proprietary (Open source code, commercial use requires license)
**Copyright**: Veritas Aequitas Holdings LLC

### Milestones

- Phase 1: Foundation (FastAPI, Streamlit, LLM providers, content policies)
- Phase 2: Scenario Generation (8 industries, hierarchical generation)
- Phase 3: Interactive War Gaming (AI Game Master, session management)
- Phase 3.5: UI Integration & Code Quality (end-to-end functionality, enterprise standards)
- Phase 4: Enhanced Safety & Policies (content filtering, audit logging, compliance tracking)
- Phase 5A: Core Game Mechanics (objectives, system states, threat responses)
- Phase 5B: Enhanced Game Mechanics (business impact, time pressure, resource constraints)
- Phase 6: Analytics & After Action Review (decision analysis, PDF reports, alternative paths)
- Phase 7: Advanced Features (adaptive AI, auth, scenario library, webhooks)
- Phase 8: Deployment & Scaling (Docker, CI/CD, monitoring, security hardening)
- Phase 9: Market Positioning (MITRE ATT&CK, multi-team exercises, compliance scoring, executive dashboard)
- Phase 10: Production Readiness (full test coverage, integration fixes, shared fixtures)

---

## Project Structure

```
ai_tabletop_world_builder/
├── Documentation
│   ├── README.md                    # Main documentation
│   ├── QUICKSTART.md                # 5-minute setup guide
│   ├── ROADMAP.md                   # Development roadmap
│   ├── CHANGELOG.md                 # Version history
│   ├── CONTRIBUTING.md              # Contributor guidelines
│   ├── COMMERCIAL_LICENSE.md        # Commercial licensing info
│   └── LICENSE                      # Legal terms
│
├── Configuration
│   ├── .env.example                 # Environment template
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Container build
│   ├── docker-compose.yml           # Multi-service orchestration
│   └── .gitignore                   # Git exclusions
│
├── Backend - FastAPI
│   ├── main.py                      # API entry point (81 routes)
│   ├── config/                      # Settings management
│   ├── api/models/                  # Pydantic schemas
│   ├── api/providers/               # LLM abstraction (OpenAI, Anthropic, Ollama)
│   ├── api/services/                # 37 business logic services
│   ├── api/routers/                 # 12 API routers
│   ├── api/middleware/              # Auth middleware
│   └── api/utils/                   # Logging, pattern matching
│
├── Frontend - Streamlit
│   ├── app/Home.py                  # Main dashboard with full navigation
│   ├── app/config.py                # Centralized configuration
│   ├── app/constants.py             # UI <-> API value mappings
│   └── app/pages/                   # 12 pages (see below)
│
├── Data & Storage
│   ├── scenarios/generated/         # Generated training scenarios
│   ├── data/                        # Application data (sessions, exercises)
│   └── data/inject_templates/       # Crisis inject templates
│
├── Testing
│   ├── conftest.py                  # Shared test fixtures
│   └── test_*.py                    # 24 test files (241 tests)
│
└── Infrastructure
    ├── monitoring/                   # Observability configs
    └── .github/workflows/           # CI/CD pipeline
```

---

## Platform Metrics

| Metric | Value |
|--------|-------|
| **Python Files** | 120 |
| **Lines of Code** | ~31,000 |
| **Services** | 37 |
| **API Routes** | 81 |
| **API Routers** | 12 |
| **UI Pages** | 12 |
| **Test Files** | 24 |
| **Tests** | 241 (240 passed, 1 skipped) |
| **Industries** | 8 |
| **Player Roles** | 4 |
| **MITRE Techniques** | 93 |
| **Compliance Frameworks** | 3 (NIST CSF, PCI DSS, HIPAA) |

---

## Services (37)

### Core Game Services
| Service | Description |
|---------|-------------|
| `game_orchestrator.py` | Coordinates game sessions and AI game master |
| `game_session_service.py` | Session persistence and lifecycle management |
| `game_master_service.py` | LLM-driven narrative generation |
| `scenario_orchestrator.py` | Hierarchical scenario generation pipeline |

### Generator Services
| Service | Description |
|---------|-------------|
| `organization_generator.py` | Industry-specific organization generation |
| `department_generator.py` | Business department generation |
| `system_generator.py` | IT infrastructure generation |
| `vulnerability_generator.py` | CVE-based vulnerability generation |
| `threat_actor_generator.py` | Threat actor profile generation |
| `objective_generator.py` | Training objective generation |

### Game Mechanics Services
| Service | Description |
|---------|-------------|
| `system_state_manager.py` | Real-time system health tracking |
| `threat_response_engine.py` | Dynamic threat actor behavior |
| `business_impact_service.py` | Financial impact calculations |
| `time_pressure_service.py` | Countdown timers and escalation |
| `resource_manager.py` | Action points, budget, staff management |

### Safety & Compliance Services
| Service | Description |
|---------|-------------|
| `content_policy_service.py` | Four-tier content policy system |
| `action_filter_service.py` | Pre-action content checking (32 patterns) |
| `content_validator_service.py` | Post-generation AI output validation |
| `audit_log_service.py` | SHA256-hashed audit trail |
| `violation_handler_service.py` | Automated violation responses |
| `compliance_scoring_service.py` | NIST/PCI/HIPAA compliance scoring |

### Analytics & Reporting Services
| Service | Description |
|---------|-------------|
| `decision_analyzer.py` | Decision quality scoring |
| `alternative_path_service.py` | Alternative path suggestions |
| `aar_service.py` | After Action Review generation |
| `report_generator.py` | PDF report export |
| `executive_dashboard_service.py` | Ponemon-calibrated executive metrics |

### Exercise Services
| Service | Description |
|---------|-------------|
| `exercise_orchestrator.py` | Multi-team exercise coordination |
| `exercise_store.py` | Exercise state persistence |
| `inject_service.py` | Crisis inject engine (20 templates, 6 heuristics) |
| `mitre_attack_service.py` | MITRE ATT&CK integration (93 techniques) |

### Infrastructure Services
| Service | Description |
|---------|-------------|
| `llm_service.py` | LLM completion management |
| `auth_service.py` | JWT authentication with Argon2id |
| `api_key_service.py` | External API key management |
| `webhook_service.py` | Event notification webhooks |
| `scenario_library_service.py` | Pre-built scenario templates |
| `adaptive_difficulty_service.py` | Dynamic difficulty adjustment |
| `training_path_service.py` | Personalized training recommendations |

---

## UI Pages (12)

| Page | Category | Description |
|------|----------|-------------|
| **Scenario Builder** | Build | Generate training scenarios |
| **Scenario Editor** | Build | Customize generated scenarios (6 tabs) |
| **Scenario Library** | Build | Browse pre-built scenario templates |
| **War Game** | Play | Interactive incident response simulation |
| **Exercise Setup** | Play | Configure multi-team tabletop exercises |
| **Exercise Play** | Play | Live exercise play with team coordination |
| **Analytics** | Analyze | Performance dashboards and metrics |
| **After Action Review** | Analyze | AAR generation with PDF export |
| **Executive Dashboard** | Analyze | Financial impact and compliance metrics |
| **Settings** | Admin | Platform configuration and safety settings |
| **Session Manager** | Admin | Manage game sessions |
| **Login** | Admin | Authentication |

---

## API Routers (12)

| Router | Prefix | Description |
|--------|--------|-------------|
| `llm.py` | `/llm` | LLM completions and provider status |
| `content_policy.py` | `/content-policy` | Content safety checking |
| `scenarios.py` | `/scenarios` | Scenario generation and management |
| `game.py` | `/game` | War gaming sessions and actions |
| `settings.py` | `/settings` | Platform configuration |
| `audit.py` | `/audit` | Audit logs and compliance reports |
| `analytics.py` | `/analytics` | Performance analytics and AAR |
| `auth.py` | `/auth` | Authentication and authorization |
| `mitre.py` | `/mitre` | MITRE ATT&CK techniques |
| `exercise.py` | `/exercise` | Multi-team exercise management |
| `library.py` | `/library` | Scenario library |
| `integrations.py` | `/integrations` | Webhooks and API keys |

---

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Server**: Uvicorn (ASGI)
- **Validation**: Pydantic v2
- **Config**: pydantic-settings
- **Auth**: JWT + Argon2id
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: Streamlit
- **Analytics**: pandas
- **Styling**: Native Streamlit

### LLM Providers
- **OpenAI**: GPT-4, GPT-3.5
- **Anthropic**: Claude 3.5/4
- **Ollama**: Llama 3, Mistral (local)

### Infrastructure
- **Language**: Python 3.11+
- **Container**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: OpenTelemetry
- **Storage**: JSON files (file-based persistence)

---

## Business Model

### Target Market
- Security training providers
- Enterprise security teams
- MSSPs and consulting firms
- Educational institutions
- Government agencies

### Revenue Streams
1. **SaaS Subscriptions** (Primary)
2. **Commercial Licenses** (On-premise, white-label)
3. **Professional Services** (Custom scenarios, training)
4. **Partner Program** (Reseller, integrations)

---

## License

**License Type**: Proprietary with open source code

**Permitted**:
- View source code
- Fork for personal development
- Contribute to project
- Use for learning/evaluation

**Requires Commercial License**:
- Business/commercial use
- SaaS deployment
- Production environments
- Training services for profit

---

**Last Updated**: 2026-02-20
**Version**: 1.0.0
**Status**: Phase 10 Production Readiness Complete
