# Cybersecurity War Gaming Platform

An AI-powered tabletop war gaming platform for IT/Security team training. Generate realistic cybersecurity scenarios and practice incident response, threat detection, and defensive security operations.

## Overview

This platform adapts the AI tabletop RPG framework to create **customized cybersecurity exercises** for training purposes. Instead of fantasy worlds, it generates realistic organizations with IT infrastructure, vulnerabilities, and threat scenarios for security teams to practice their skills.

### Key Features

- **Hierarchical Scenario Generation**: Create realistic organizations with complete IT infrastructure
  - Organizations → Departments → Systems → Vulnerabilities/Threats
  - Industry-specific configurations (Finance, Healthcare, Tech, etc.)
  - Customizable complexity and scope

- **Interactive War Gaming**: Real-time incident response simulation
  - AI-powered threat actor behavior
  - Realistic incident timelines
  - Tool and access management
  - Decision consequence simulation

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
├── services/        # Business logic
├── routers/         # API endpoints
└── main.py          # FastAPI application
```

### Frontend (Streamlit)
```
app/
├── Home.py                      # Main dashboard with system status
├── config.py                    # Centralized configuration
├── constants.py                 # UI ↔ API value mappings
└── pages/
    ├── 1_Scenario_Builder.py   # Generate training scenarios
    ├── 2_War_Game.py            # Interactive war gaming
    ├── 3_Settings.py            # Platform configuration
    ├── 4_Session_Manager.py     # Manage game sessions
    └── 5_Scenario_Editor.py     # Customize generated scenarios
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

- Python 3.10+
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

**Option 2: Quick start script (coming soon)**
```bash
./start.sh  # Starts both services
```

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

### 4. Review Performance

After completing the scenario:
- View incident timeline
- Analyze decisions made
- Review scoring and feedback
- Identify areas for improvement

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

### FastAPI Endpoints

**LLM Service:**
- `POST /llm/complete` - Generate LLM completion
- `GET /llm/providers` - Check provider availability

**Content Policy:**
- `POST /content-policy/check` - Verify content safety
- `GET /content-policy/policies` - List available policies

**Scenarios:** ✅ **IMPLEMENTED**
- `POST /scenarios/generate` - Generate training scenario
- `GET /scenarios/list` - List all saved scenarios
- `GET /scenarios/industries` - List supported industries
- `GET /scenarios/industries/{industry}` - Get industry details
- `GET /scenarios/{filename}` - Load scenario by filename
- `DELETE /scenarios/{filename}` - Delete saved scenario

**Game:** ✅ **IMPLEMENTED**
- `POST /game/start` - Start new war gaming session
- `POST /game/action` - Process player action
- `GET /game/state/{session_id}` - Get current game state
- `POST /game/hint` - Request contextual hint
- `POST /game/end` - End game session
- `GET /game/sessions` - List all sessions with optional filter
- `DELETE /game/sessions/{session_id}` - Delete game session
- `POST /game/objective` - Mark objective as completed/failed

**Settings:** ✅ **IMPLEMENTED**
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
│   ├── models/            # Data schemas
│   ├── providers/         # LLM provider implementations
│   ├── services/          # Business logic
│   └── routers/           # API endpoints
├── app/                   # Streamlit frontend
│   ├── Home.py           # Main page
│   └── pages/            # Multi-page app
├── config/               # Configuration
├── scenarios/            # Generated scenarios
├── data/                 # Storage
├── utils/                # Shared utilities
├── tests/                # Unit tests
├── context/              # Course materials
├── main.py               # FastAPI entry point
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Adding New Features

**To add a new LLM provider:**
1. Create provider class in `api/providers/`
2. Inherit from `BaseLLMProvider`
3. Implement `complete()` method
4. Add to `LLMProviderFactory`

**To add a new content policy:**
1. Add policy configuration to `ContentPolicyService.POLICIES`
2. Define allowed/blocked categories
3. Update settings options

**To add a new page:**
1. Create file in `app/pages/`
2. Use format: `N_Page_Name.py`
3. Import and configure streamlit

### Running Tests

```bash
pytest tests/
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
- **Audit Logging**: All actions logged for compliance (coming soon)

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- Code of conduct
- Development setup
- Coding standards
- Pull request process
- Areas for contribution

**Note**: By contributing, you agree to the terms in the [LICENSE](LICENSE) file, including that your contributions may be used in both open-source and commercial versions of the platform.

## License

Copyright (c) 2025 [Your Name/Company]. All Rights Reserved.

This project is licensed under a **proprietary license** with the following key terms:

- ✅ **Free for evaluation, learning, and personal development**
- ✅ **Open source code for transparency and community contributions**
- ❌ **Commercial use requires a separate commercial license**
- ❌ **Cannot be used for SaaS offerings without permission**

**Why this license?**
We want to:
- Keep the code open for learning and contributions
- Build a strong community around security training
- Monetize as SaaS to sustain development and provide enterprise features
- Offer commercial licenses for organizations that want to deploy internally

**Commercial Licensing**: Interested in using this for your business? Contact us about:
- Enterprise deployments
- White-label solutions
- Custom features and integrations
- Priority support and SLAs

See [LICENSE](LICENSE) file for full terms or contact [your-email@example.com] for commercial inquiries.

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
- Open an issue on GitHub
- Check documentation
- Review course materials in `/context`

---

**Version**: 0.5.0
**Status**: Phase 5A Core Mechanics Complete - Advanced War Gaming with Dynamic Mechanics
**Last Updated**: 2025-11-04

## Recent Updates (v0.5.0) - PHASE 5A COMPLETE! 🎉

✅ **Automatic Objective Generation**: AI-powered objective creation from scenarios
✅ **System State Tracking**: Real-time health and status monitoring (online/compromised/recovering)
✅ **Dynamic Threat Responses**: Threats react to player actions with escalation and evasion
✅ **3 New Services**: ~1,110 lines of intelligent game mechanics
✅ **3 Real-Time Dashboards**: Objectives, Systems, and Threats with visual indicators
✅ **Sophistication-Based Behavior**: Threat aggression scales with capability
✅ **Contextual Generation**: Objectives match scenario vulnerabilities and threats
✅ **All Core Mechanics Working**: Complete end-to-end dynamic gameplay

### Previous Updates (v0.4.0)
✅ UI Integration Complete | ✅ Scenario Editor (6 tabs) | ✅ Session Management
✅ Settings with .env persistence | ✅ 20 API Endpoints | ✅ Enterprise code quality

See [CHANGELOG.md](CHANGELOG.md) for complete details.
