# Quick Start Guide

Get up and running with the Cybersecurity War Gaming Platform in 5 minutes.

## ⚡ Quick Setup

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API key
# For OpenAI (recommended):
OPENAI_API_KEY=sk-your-key-here
DEFAULT_LLM_PROVIDER=openai

# OR for Anthropic:
ANTHROPIC_API_KEY=sk-ant-your-key-here
DEFAULT_LLM_PROVIDER=anthropic

# OR for local Ollama (free, requires GPU):
# 1. Install Ollama from https://ollama.ai
# 2. Pull a model: ollama pull llama3
DEFAULT_LLM_PROVIDER=ollama
```

### 3. Start the Platform

**Terminal 1 - Backend:**
```bash
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd app
streamlit run Home.py
```

### 4. Access the Platform

- **Web UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

## First War Game

### Step 1: Configure Settings (Settings Page)

1. Select your LLM provider
2. Enter API key
3. Click "Test Connection"
4. Choose content policy level:
   - **Educational** (recommended for first time)
5. Save settings

### Step 2: Generate Scenario (Scenario Builder)

1. Select industry (e.g., "Financial Services")
2. Choose organization size (e.g., "Medium")
3. Set difficulty to "Beginner"
4. Add focus area: "Ransomware"
5. Select player role: "SOC Analyst"
6. Click "Generate Scenario"
7. Review the generated organization and threats
8. Click "Start War Game"

### Step 3: Play War Game (🎮 War Game Page)

1. Click "Start Incident"
2. Read the initial alert
3. Type your response:
   ```
   Check SIEM logs for related events
   ```
4. See AI respond with scenario development
5. Continue investigating and responding
6. Use hints if needed
7. Complete objectives

### Step 4: Review Performance

- Check incident timeline
- Review decisions made
- Analyze scoring
- Identify improvements

## Example Session

**Scenario**: Ransomware attack on financial institution

**Initial Alert**:
```
SECURITY ALERT
Time: 09:45 AM
Source: EDR System
Severity: HIGH
Description: Suspicious PowerShell execution detected
```

**Your Actions** (examples):
1. "Check SIEM for related alerts in the last hour"
2. "Isolate the affected workstation from the network"
3. "Check for lateral movement to other systems"
4. "Review recent phishing emails sent to this user"
5. "Escalate to incident response team"

**AI Responses**:
- Provides realistic findings
- Shows consequences of actions
- Updates threat status
- Tracks your decisions
- Scores your response

## Training Paths

### Path 1: Beginner SOC Analyst
1. Phishing investigation (30 min)
2. Malware detection (45 min)
3. Basic incident response (60 min)

### Path 2: Intermediate IR Specialist
1. Ransomware response (90 min)
2. Data breach investigation (120 min)
3. Business email compromise (90 min)

### Path 3: Advanced Security Engineer
1. APT threat hunting (180 min)
2. Zero-day response (120 min)
3. Supply chain attack (150 min)

## Configuration Options

### Content Policy Levels

| Level | Use Case | Suitable For |
|-------|----------|--------------|
| **Defensive** | Basic security training | Beginners, compliance-sensitive |
| **Educational** | Realistic training | Most security teams |
| **Advanced** | Red/Blue team exercises | Experienced professionals |
| **Unrestricted** | Full realism | Expert researchers |

### LLM Providers

**OpenAI** (Recommended)
- Best quality responses
- Cost: ~$0.03 per 1K tokens
- Models: GPT-4, GPT-3.5

**Anthropic**
- Excellent reasoning
- Similar cost to OpenAI
- Models: Claude 3.5 Sonnet

**Ollama** (Local)
- Free, runs on your hardware
- Requires GPU (8GB+ VRAM recommended)
- Models: Llama 3, Mistral

## Troubleshooting

### "API connection failed"
```bash
# Check your .env file
cat .env | grep API_KEY

# Test the API directly
curl http://localhost:8000/health
```

### "Provider not available"
```bash
# For OpenAI/Anthropic: verify API key
# For Ollama: ensure it's running
ollama serve

# Check model is pulled
ollama list
```

### "Streamlit won't start"
```bash
# Clear cache
streamlit cache clear

# Ensure you're in app directory
cd app
streamlit run Home.py
```

## Tips

- Start with "Educational" policy
- Use hints liberally while learning
- Review After Action Reports
- Practice regularly
- Increase difficulty gradually
- Customize scenarios to your environment

## Getting Help

- **Documentation**: See README.md
- **API Docs**: http://localhost:8000/docs
- **Course Materials**: Check `/context` folder
- **Issues**: Open GitHub issue

---

**Ready to start?** Run the commands above and visit http://localhost:8501

Happy war gaming!
