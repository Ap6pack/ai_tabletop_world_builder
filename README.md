# Cybersecurity War Gaming Platform

An **open-source** (Apache-2.0), AI-powered tabletop war-gaming platform for IT/security team training. Generate realistic cybersecurity scenarios, run AI game-master incident simulations, and produce after-action reports — MITRE ATT&CK-aware, on a FastAPI + Streamlit stack with PostgreSQL storage.

## Overview

This platform adapts the AI tabletop RPG framework to create **customized cybersecurity exercises** for training purposes. Instead of fantasy worlds, it generates realistic organizations with IT infrastructure, vulnerabilities, and threat scenarios for security teams to practice their skills.

### Key Features

- **Hierarchical Scenario Generation**: Create realistic organizations with complete IT infrastructure
  - Organizations -> Departments -> Systems -> Vulnerabilities/Threats
  - Industry-specific configurations (Finance, Healthcare, Tech, etc.)
  - Customizable complexity and scope

- **Interactive War Gaming**: Real-time incident response simulation
  - AI-powered threat actor behavior
  - Realistic incident timelines
  - Tool and access management
  - Decision consequence simulation

- **Multi-Team Tabletop Exercises**: Coordinated team-based exercises
  - Blue/Red/White team roles with polling-based coordination
  - MITRE ATT&CK integration (93 techniques across 14 tactics)
  - Crisis inject engine with 20 templates and 6 heuristics
  - Real-time exercise orchestration

- **Executive & Compliance Dashboard**: Strategic reporting
  - Executive dashboard with Ponemon-calibrated financial metrics
  - Compliance scoring for NIST CSF, PCI DSS, and HIPAA frameworks
  - After Action Review (AAR) generation with PDF export
  - Decision quality analysis and alternative path suggestions

- **Flexible Content Policies**: Multiple training levels
  - **Defensive**: Security monitoring and controls only
  - **Educational**: Realistic scenarios with defensive focus
  - **Advanced**: Red team tactics for experienced teams
  - **Unrestricted**: Full realism for expert training

- **Performance Tracking**: Monitor and improve
  - Real-time incident dashboards
  - Decision tracking and scoring
  - After Action Reviews (AAR)
  - Team performance analytics

## Architecture

### Backend (FastAPI)
```
api/
├── models/          # Pydantic data models
├── providers/       # LLM provider abstraction (OpenAI, Anthropic, Ollama)
├── services/        # 37 business logic services
├── routers/         # 12 API routers (81 routes)
├── middleware/       # Auth middleware
└── main.py          # FastAPI application
```

### Frontend (Streamlit)
```
app/
├── Home.py                       # Main dashboard with full navigation
├── config.py                     # Centralized configuration
├── constants.py                  # UI <-> API value mappings
└── pages/
    ├── 1_Scenario_Builder.py     # Generate training scenarios
    ├── 2_War_Game.py             # Interactive war gaming
    ├── 3_Settings.py             # Platform configuration
    ├── 4_Session_Manager.py      # Manage game sessions
    ├── 5_Scenario_Editor.py      # Customize generated scenarios
    ├── 6_Analytics.py            # Performance analytics
    ├── 7_After_Action_Review.py  # AAR review and PDF export
    ├── 8_Login.py                # Authentication
    ├── 9_Scenario_Library.py     # Scenario library browser
    ├── 10_Exercise_Setup.py      # Multi-team exercise setup
    ├── 11_Exercise_Play.py       # Live exercise play
    └── 12_Executive_Dashboard.py # Executive metrics dashboard
```

### Data Models

**Organization Hierarchy:**
```python
Organization
├── Departments (Finance, IT, HR, etc.)
│   └── Systems (Servers, Applications, Networks)
│       └── Vulnerabilities & Security Controls
└── Threat Actors (APT, Ransomware, Insider, etc.)
```

**Game State:**
- Player role and permissions
- Available security tools
- Incident timeline
- Objectives and scoring

## Getting Started

### Prerequisites

- Python 3.11+
- API key for at least one LLM provider:
  - OpenAI (recommended)
  - Anthropic Claude
  - Ollama (local, free)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Ap6pack/ai_tabletop_world_builder.git
cd ai_tabletop_world_builder
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys and preferences
```

### Configuration

Edit `.env` file with your settings:

```bash
# Choose your LLM provider
DEFAULT_LLM_PROVIDER=openai  # or anthropic, ollama

# Add API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Set content policy
DEFAULT_CONTENT_POLICY=educational  # defensive, educational, advanced, unrestricted
```

### Running the Platform

**Option 1: Run both services separately**

Terminal 1 - Start FastAPI backend:
```bash
python main.py
# API will run on http://localhost:8000
# API docs: http://localhost:8000/docs
```

Terminal 2 - Start Streamlit frontend:
```bash
cd app
streamlit run Home.py
# Web UI will open at http://localhost:8501
```

**Option 2: Docker (Postgres-backed)**
```bash
docker-compose up
```
The Compose stack runs the API against the bundled **PostgreSQL** and Redis
services automatically (it sets `DATABASE_URL`/`REDIS_URL` for you). Override the
database credentials with `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

## Database

Mutable application state — users, game sessions, exercises, API keys, and
webhooks — is stored via SQLAlchemy. The backend is chosen entirely by the
`DATABASE_URL` environment variable, so the same code runs on either:

- **Local development (default): SQLite** — zero setup, a file at `./data/app.db`.
- **Production: PostgreSQL** (recommended). Point at a managed instance:
  ```bash
  DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
  ```
  The `psycopg` driver is already in `requirements.txt`. The API is stateless,
  so you can run multiple instances behind a load balancer against one Postgres.

**Schema migrations:** managed with [Alembic](https://alembic.sqlalchemy.org).
For a fresh database run `alembic upgrade head` before starting the app; on
subsequent schema changes, generate a migration with
`alembic revision --autogenerate -m "describe change"` and apply it with
`alembic upgrade head`. (For quick local/dev use the app also creates any missing
tables on startup.)

**Redis (optional):** live multi-team exercises can use Redis as a low-latency
fast-path — set `REDIS_URL=redis://host:6379/0`. Without it, exercise state is
served from the database. Audit logs are append-only JSONL by design.

## Usage Guide

### 1. Configure LLM Provider

Go to **Settings** page and configure your LLM provider:
- Select provider (OpenAI, Anthropic, or Ollama)
- Enter API key
- Test connection
- Set content policy level

### 2. Generate a Scenario

Go to **Scenario Builder** page:
- Select industry (Finance, Healthcare, Tech, etc.)
- Choose organization size
- Set complexity and difficulty
- Define focus areas (Ransomware, APT, Insider threats, etc.)
- Select player role (SOC Analyst, CISO, etc.)
- Click "Generate Scenario"

### 3. Start War Game

From the generated scenario:
- Review organization details
- Check threat landscape
- Click "Start War Game"
- Respond to incidents in real-time
- Use available security tools
- Make decisions and see consequences

### 4. Run Multi-Team Exercises

Go to **Exercise Setup** page:
- Configure Blue/Red/White teams
- Set exercise parameters and MITRE ATT&CK techniques
- Load crisis inject templates
- Launch exercise and play through rounds

### 5. Review Performance

After completing the scenario:
- View incident timeline on Analytics page
- Generate After Action Reviews with PDF export
- Review executive dashboard for financial impact
- Check compliance scoring against NIST/PCI/HIPAA

## Training Scenarios

### Example Scenarios

**Beginner: Phishing Investigation**
- Duration: 30 minutes
- Role: SOC Analyst
- Focus: Email analysis, user education
- Tools: SIEM, Email gateway

**Intermediate: Ransomware Response**
- Duration: 90 minutes
- Role: Incident Responder
- Focus: Containment, recovery, communication
- Tools: EDR, Firewall, Backup systems

**Advanced: APT Threat Hunting**
- Duration: 180 minutes
- Role: Security Engineer
- Focus: Threat detection, lateral movement, forensics
- Tools: Full security stack

## API Documentation

### FastAPI Endpoints (81 routes across 12 routers)

**LLM Service:**
- `POST /llm/complete` - Generate LLM completion
- `GET /llm/providers` - Check provider availability

**Content Policy:**
- `POST /content-policy/check` - Verify content safety
- `GET /content-policy/policies` - List available policies

**Scenarios:**
- `POST /scenarios/generate` - Generate training scenario
- `GET /scenarios/list` - List all saved scenarios
- `GET /scenarios/industries` - List supported industries
- `GET /scenarios/industries/{industry}` - Get industry details
- `GET /scenarios/{filename}` - Load scenario by filename
- `DELETE /scenarios/{filename}` - Delete saved scenario

**Game:**
- `POST /game/start` - Start new war gaming session
- `POST /game/action` - Process player action
- `GET /game/state/{session_id}` - Get current game state
- `POST /game/hint` - Request contextual hint
- `POST /game/end` - End game session
- `GET /game/sessions` - List all sessions with optional filter
- `DELETE /game/sessions/{session_id}` - Delete game session
- `POST /game/objective` - Mark objective as completed/failed

**MITRE ATT&CK:**
- `GET /mitre/techniques` - List techniques by tactic
- `GET /mitre/matrix` - Full ATT&CK matrix

**Exercises:**
- `POST /exercise/create` - Create multi-team exercise
- `POST /exercise/advance` - Advance exercise round
- `GET /exercise/state` - Get exercise state

**Analytics & Reporting:**
- `GET /analytics/session/{session_id}` - Session analytics
- `POST /analytics/aar` - Generate After Action Review

**Settings:**
- `GET /settings/current` - Get current configuration
- `POST /settings/update` - Update settings and persist to .env
- `GET /settings/storage/stats` - Real-time storage statistics
- `POST /settings/export` - Export configuration as JSON
- `DELETE /settings/data/clear` - Delete all data
- `POST /settings/reset/defaults` - Reset to defaults

API documentation available at: `http://localhost:8000/docs`

## Development

### Project Structure

```
ai_tabletop_world_builder/
├── api/                    # FastAPI backend
│   ├── models/             # Data schemas
│   ├── providers/          # LLM provider implementations
│   ├── services/           # 37 business logic services
│   ├── routers/            # 12 API routers
│   ├── middleware/         # Auth middleware
│   └── utils/              # Shared utilities
├── app/                    # Streamlit frontend
│   ├── Home.py             # Main page
│   └── pages/              # 12 pages
├── tests/                  # 25 test files (245 tests)
├── docs/                   # Phase completion & planning docs
├── scripts/                # Shell scripts and utilities
├── config/                 # Configuration
├── scenarios/              # Generated scenarios
├── data/                   # Storage
├── monitoring/             # Observability configs
├── main.py                 # FastAPI entry point
├── Dockerfile              # Container build
├── docker-compose.yml      # Multi-service orchestration
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

### Running Tests

```bash
pytest --tb=short -q
# 244 passed, 1 skipped
# Tests are hermetic — no API key or network required (a fake LLM provider is
# injected via tests/conftest.py). Tests are in the tests/ directory.
```

## Content Policy Levels

| Level | Description | Use Case | Includes | Excludes |
|-------|-------------|----------|----------|----------|
| **Defensive** | Defensive security only | Beginner teams, compliance-sensitive | Monitoring, incident response, controls | Exploit code, offensive techniques |
| **Educational** | Realistic with defensive focus | SOC training, security awareness | Vulnerability concepts, threat modeling | Actual exploits, real credentials |
| **Advanced** | Realistic attack/defense | Experienced teams, red/blue exercises | Red team tactics, exploitation theory | Production exploits, illegal activities |
| **Unrestricted** | Full realism | Expert researchers, controlled environments | Detailed exploitation, advanced TTPs | Illegal activities |

## Security Considerations

- **API Keys**: Never commit API keys. Use `.env` file
- **Content Policy**: Set appropriate policy for your team's skill level
- **Data Privacy**: Scenarios and game data stored locally
- **Audit Logging**: All actions logged with SHA256 hashing for compliance
- **Auth**: JWT-based authentication with Argon2id password hashing. Set
  `REQUIRE_AUTH=true` (and a strong `JWT_SECRET_KEY`) to enforce it: product
  endpoints then require a valid bearer token and destructive admin operations
  (`/settings/data/clear`, `/settings/update`, config writes) require the
  `admin` role. With auth disabled (the local/dev default) endpoints are open.
  Note: the Streamlit UI does not yet attach tokens, so run it against an
  auth-disabled API or behind an authenticating gateway.
- **Rate Limiting**: Fixed-window limits on all API endpoints, keyed per
  authenticated user (or client IP when anonymous), to protect LLM-backed
  endpoints from abuse. Configure via `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`,
  and `RATE_LIMIT_WINDOW_SECONDS`; uses Redis (`REDIS_URL`) for shared limits
  across instances, otherwise an in-process counter.

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- Code of conduct
- Development setup
- Coding standards
- Pull request process
- Areas for contribution

**Note**: By contributing, you agree that your contributions are licensed under the project's Apache-2.0 license.

## License

Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors.

Licensed under the **Apache License, Version 2.0**. This is free, open-source
software — you may use, modify, and distribute it, including for commercial
purposes, under the terms of that license (which also includes an explicit
patent grant). See the [LICENSE](LICENSE) file for the full text.

## Resources

- [API Documentation](http://localhost:8000/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Streamlit Docs](https://docs.streamlit.io/)

## Troubleshooting

**API connection failed:**
- Check API key is set correctly in `.env`
- Verify provider is available (test at `/llm/providers`)
- Check network connectivity

**Ollama not working:**
- Ensure Ollama is running: `ollama serve`
- Pull required model: `ollama pull llama3`
- Check base URL in settings

**Streamlit page not loading:**
- Ensure you're in `/app` directory
- Check FastAPI backend is running
- Clear Streamlit cache: `streamlit cache clear`

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/Ap6pack/ai_tabletop_world_builder/issues)
- Check the documentation

---

**Version**: 1.0.0
**Status**: Active development — core platform functional and CI green. Mutable
state (users, sessions, exercises, API keys, webhooks) is stored via SQLAlchemy
(SQLite by default, Postgres-ready via `DATABASE_URL`). Authentication is
enforced when `REQUIRE_AUTH=true` (product endpoints need a token; admin
endpoints need the `admin` role) — see [DEPLOY.md](DEPLOY.md) for production setup.
**Last Updated**: 2026-07-18

See [CHANGELOG.md](CHANGELOG.md) for complete details.
