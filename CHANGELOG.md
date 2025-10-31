# Changelog

All notable changes to the Cybersecurity War Gaming Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Hierarchical scenario generation (Phase 2)
- Interactive war gaming engine (Phase 3)
- After Action Review system (Phase 6)
- Multi-user support (Phase 7)

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
- **0.2.0** - Planned: Scenario generation (Phase 2)
- **0.3.0** - Planned: Interactive war gaming (Phase 3)
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

[Unreleased]: https://github.com/Ap6pack/ai_tabletop_world_builder/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Ap6pack/ai_tabletop_world_builder/releases/tag/v0.1.0
