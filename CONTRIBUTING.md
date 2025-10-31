# Contributing to Cybersecurity War Gaming Platform

Thank you for your interest in contributing to the Cybersecurity War Gaming Platform! This document provides guidelines and instructions for contributing to the project.

## 🎯 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Contribution Guidelines](#contribution-guidelines)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)
- [Communication](#communication)

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background or experience level. We expect all participants to:

- Be respectful and professional
- Accept constructive criticism gracefully
- Focus on what's best for the project and community
- Show empathy towards other community members
- Respect differing viewpoints and experiences

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.10 or higher
- Git installed and configured
- A GitHub account
- Basic understanding of FastAPI and Streamlit (or willingness to learn)
- Familiarity with cybersecurity concepts (helpful but not required)

### First-Time Contributors

New to open source? Welcome! Here are some good starting points:

1. **Read the documentation**:
   - [README.md](README.md) - Project overview
   - [QUICKSTART.md](QUICKSTART.md) - Setup guide
   - [ROADMAP.md](ROADMAP.md) - Development plan

2. **Look for beginner-friendly issues**:
   - Issues labeled `good-first-issue`
   - Issues labeled `documentation`
   - Issues labeled `help-wanted`

3. **Ask questions**:
   - Open a discussion on GitHub
   - Comment on issues you're interested in
   - Don't be afraid to ask for help!

## 💻 Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ai_tabletop_world_builder.git
cd ai_tabletop_world_builder

# Add upstream remote
git remote add upstream https://github.com/Ap6pack/ai_tabletop_world_builder.git
```

### 2. Create Virtual Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio black flake8 mypy
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys for testing
# At minimum, configure one LLM provider
```

### 4. Verify Setup

```bash
# Run tests
pytest tests/

# Start backend
python main.py

# In another terminal, start frontend
cd app
streamlit run Home.py
```

### 5. Create Feature Branch

```bash
# Create a branch for your contribution
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

## 🤝 How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Code**: New features, bug fixes, improvements
- **Documentation**: README updates, tutorials, examples
- **Testing**: Unit tests, integration tests, test coverage
- **Design**: UI/UX improvements, mockups
- **Ideas**: Feature requests, architectural suggestions
- **Bug Reports**: Identifying and reporting issues

### Reporting Bugs

When reporting bugs, please include:

1. **Clear title**: Brief description of the issue
2. **Description**: What happened vs. what you expected
3. **Steps to reproduce**:
   ```
   1. Go to...
   2. Click on...
   3. See error...
   ```
4. **Environment**:
   - OS (Linux/macOS/Windows)
   - Python version
   - LLM provider used
   - Browser (for Streamlit issues)
5. **Logs/Screenshots**: Error messages, stack traces
6. **Additional context**: Anything else that might help

### Suggesting Enhancements

For feature requests, please provide:

1. **Problem statement**: What problem does this solve?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches you thought of
4. **Use case**: When would this be used?
5. **Priority**: How important is this feature?

## 📋 Contribution Guidelines

### Before You Start

1. **Check existing issues**: Someone might already be working on it
2. **Discuss major changes**: Open an issue first for big features
3. **Follow the roadmap**: Align with current development phase (see [ROADMAP.md](ROADMAP.md))
4. **One feature per PR**: Keep changes focused and reviewable

### Commit Messages

Use clear, descriptive commit messages:

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(api): add organization generator endpoint

Implement hierarchical organization generation with industry-specific
templates. Supports 8 industry sectors with configurable complexity.

Closes #42

---

fix(ui): correct scenario builder form validation

Fix issue where empty focus areas caused form submission error.

Fixes #57

---

docs(readme): update installation instructions

Add troubleshooting section for common Ollama setup issues.
```

### Branch Naming

Use descriptive branch names:

```bash
feature/organization-generator
fix/scenario-builder-validation
docs/api-documentation
refactor/llm-provider-abstraction
test/game-session-unit-tests
```

## 🏗️ Project Structure

Understanding the codebase:

```
ai_tabletop_world_builder/
├── api/                    # Backend (FastAPI)
│   ├── models/            # Pydantic schemas
│   │   └── schemas.py     # Data models (Organization, System, etc.)
│   ├── providers/         # LLM provider implementations
│   │   ├── base.py        # Abstract base class
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── ollama_provider.py
│   │   └── factory.py     # Provider factory
│   ├── services/          # Business logic
│   │   ├── llm_service.py
│   │   └── content_policy_service.py
│   └── routers/           # API endpoints
│       ├── llm.py
│       └── content_policy.py
├── app/                   # Frontend (Streamlit)
│   ├── Home.py           # Main dashboard
│   └── pages/            # Multi-page app
│       ├── 1_Scenario_Builder.py
│       ├── 2_War_Game.py
│       └── 3_Settings.py
├── config/               # Configuration
│   └── settings.py       # Application settings
├── scenarios/            # Generated scenarios (JSON)
├── data/                 # Application data
├── utils/                # Shared utilities
├── tests/                # Test suite
├── context/              # Course reference materials
└── main.py               # FastAPI entry point
```

### Key Files to Know

- `api/models/schemas.py` - All data models
- `api/providers/factory.py` - LLM provider abstraction
- `api/services/` - Core business logic
- `app/Home.py` - Main UI entry point
- `config/settings.py` - Configuration system

## 💎 Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with some modifications:

```python
# Good
def generate_organization(
    industry: str,
    size: OrganizationSize,
    complexity: Complexity = Complexity.MODERATE
) -> Organization:
    """
    Generate a realistic organization for training scenarios.

    Args:
        industry: Industry sector (e.g., "Finance", "Healthcare")
        size: Organization size enum
        complexity: Scenario complexity level

    Returns:
        Organization instance with complete infrastructure

    Raises:
        ValueError: If industry is not supported
    """
    if industry not in SUPPORTED_INDUSTRIES:
        raise ValueError(f"Unsupported industry: {industry}")

    # Implementation here
    pass
```

### Code Formatting

```bash
# Format code with Black
black .

# Check with flake8
flake8 api/ app/ --max-line-length=100

# Type checking with mypy
mypy api/
```

### Type Hints

Always use type hints:

```python
# Good ✅
async def complete(
    self,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    pass

# Bad ❌
async def complete(self, prompt, temperature=0.7, max_tokens=None):
    pass
```

### Documentation

Use docstrings for all public functions, classes, and modules:

```python
class OrganizationGenerator:
    """
    Generates realistic organizations for cybersecurity training.

    This class implements hierarchical content generation, creating
    organizations with departments, systems, and vulnerabilities based
    on industry-specific templates.

    Attributes:
        llm_provider: LLM provider instance for generation
        content_policy: Content policy for safety checks

    Example:
        >>> generator = OrganizationGenerator()
        >>> org = await generator.generate(
        ...     industry="Finance",
        ...     size="medium"
        ... )
    """
    pass
```

## 🧪 Testing Guidelines

### Writing Tests

```python
# tests/test_organization_generator.py
import pytest
from api.services.organization_generator import OrganizationGenerator

@pytest.mark.asyncio
async def test_generate_organization():
    """Test basic organization generation."""
    generator = OrganizationGenerator()

    org = await generator.generate(
        industry="Finance",
        size="medium",
        complexity="moderate"
    )

    assert org.name is not None
    assert org.industry == "Finance"
    assert len(org.departments) > 0

@pytest.mark.asyncio
async def test_generate_with_invalid_industry():
    """Test that invalid industry raises ValueError."""
    generator = OrganizationGenerator()

    with pytest.raises(ValueError):
        await generator.generate(
            industry="InvalidIndustry",
            size="medium"
        )
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_organization_generator.py

# Run with coverage
pytest --cov=api --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Test Coverage

- Aim for >80% code coverage
- Test happy paths and edge cases
- Test error handling
- Mock external dependencies (LLM APIs)

## 🔄 Pull Request Process

### Before Submitting

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**:
   ```bash
   pytest
   black --check .
   flake8 api/ app/
   ```

3. **Update documentation**:
   - Update README if needed
   - Add docstrings to new code
   - Update CHANGELOG.md

4. **Self-review**:
   - Review your own changes first
   - Remove debug code, comments, print statements
   - Ensure consistent style

### Submitting PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub with:

   **Title**: Clear, descriptive (e.g., "Add organization generator with industry templates")

   **Description**:
   ```markdown
   ## Description
   Brief overview of changes

   ## Motivation
   Why is this change needed?

   ## Changes Made
   - Added organization generator service
   - Implemented industry-specific templates
   - Added unit tests for generator

   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed

   ## Screenshots (if UI changes)
   [Add screenshots here]

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] Tests added/updated
   - [ ] No breaking changes

   Closes #42
   ```

3. **Respond to feedback**:
   - Be open to suggestions
   - Make requested changes promptly
   - Ask questions if unclear

### Review Process

1. **Automated checks**: CI/CD must pass
2. **Code review**: At least one maintainer approval
3. **Testing**: Reviewers may test locally
4. **Merge**: Maintainers will merge when approved

### After Merge

1. **Delete your branch**:
   ```bash
   git branch -d feature/your-feature-name
   git push origin --delete feature/your-feature-name
   ```

2. **Update your fork**:
   ```bash
   git checkout main
   git pull upstream main
   git push origin main
   ```

## 🎯 Areas for Contribution

### High Priority (Phase 2)

**Organization Generator**:
- Industry-specific templates
- Realistic organization profiles
- Department generation logic

**System Generator**:
- IT asset generation
- Vulnerability mapping
- Security control assignment

**Threat Actor Generator**:
- Threat actor profiles
- TTP generation
- Sophistication levels

### Medium Priority (Phase 3)

**Game Session Manager**:
- Session state management
- Persistence layer
- Concurrent session handling

**AI Game Master**:
- Prompt engineering
- Response generation
- Narrative flow

**Scoring System**:
- Decision evaluation
- Performance metrics
- Time tracking

### Good First Issues

**Documentation**:
- Tutorial videos
- Example scenarios
- API usage examples
- Troubleshooting guides

**UI Improvements**:
- Better error messages
- Loading indicators
- Form validation
- Responsive design

**Testing**:
- Unit tests for existing code
- Integration tests
- End-to-end tests
- Performance tests

**Scenario Templates**:
- Pre-built scenarios
- Industry-specific templates
- Difficulty variations

## 💬 Communication

### Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, help
- **Pull Requests**: Code review, technical discussion

### Getting Help

- Check existing documentation first
- Search existing issues
- Ask in GitHub Discussions
- Be specific and provide context

### Response Times

- Issues: We aim to respond within 3 business days
- PRs: Initial review within 1 week
- Questions: Usually within 24-48 hours

## 📚 Resources

### Learning Resources

**FastAPI**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Real Python FastAPI Tutorial](https://realpython.com/fastapi-python-web-apis/)

**Streamlit**:
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Gallery](https://streamlit.io/gallery)

**Cybersecurity**:
- [MITRE ATT&CK Framework](https://attack.mitre.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

**LLM Development**:
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [Ollama Documentation](https://ollama.ai/docs)

### Related Projects

- [AI Dungeon](https://play.aidungeon.io/) - Original inspiration
- [Together AI](https://www.together.ai/) - LLM platform
- [Latitude](https://latitude.io/) - AI game development

## 🙏 Recognition

Contributors will be:
- Listed in README.md
- Credited in release notes
- Mentioned in CHANGELOG.md
- Thanked in project communications

## 📄 License and Contributions

**Important**: This project uses a **proprietary license** with specific terms for contributors.

By contributing to this project, you agree that:

1. **You retain copyright** to your contributions
2. **You grant the project owner** a perpetual, worldwide, non-exclusive, royalty-free, irrevocable license to:
   - Use your contributions in both open-source and commercial versions
   - Modify, distribute, and sublicense your contributions
   - Include your contributions in paid/commercial offerings
3. **Attribution**: You will be credited in open-source releases, but attribution is not required in commercial versions
4. **No compensation**: Contributions are voluntary and do not entitle you to compensation from commercial use

**Why this matters**:
- The project aims to monetize as a SaaS platform
- Your contributions help build a sustainable business that funds ongoing development
- You get recognition in the community and can showcase your work
- The code remains open for learning and transparency

**What you get**:
- Recognition in README, CHANGELOG, and release notes
- Experience with production-grade security training platform
- Portfolio-worthy contributions
- Potential opportunities if the business grows

If you have concerns about these terms, please reach out before contributing.

See the full [LICENSE](LICENSE) file for complete details.

---

## Questions?

Don't hesitate to ask! We're here to help:

- Open a [GitHub Discussion](https://github.com/Ap6pack/ai_tabletop_world_builder/discussions)
- Comment on relevant issues
- Review the documentation

**Thank you for contributing to making cybersecurity training more accessible and effective!** 🛡️

---

**Last Updated**: 2025-10-31
