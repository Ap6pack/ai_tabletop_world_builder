# Quick Start Guide 🚀

Welcome to the **Cybersecurity War Gaming Platform**! This guide will get you up and running in minutes.

## Quick Start

### 1. Start the Platform

```bash
# Start backend API
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 &

# Start frontend (in new terminal)
streamlit run app/Home.py
```

### 2. Access
- **Frontend**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

### 3. Generate Scenario
1. Click "Create Scenario"
2. Choose industry, size, complexity
3. Wait 30-60 seconds
4. Review generated scenario

### 4. Play War Game
1. Click "Start War Game"
2. Click "Start Incident"
3. Type actions (e.g., "Check SIEM logs")
4. Track score and timeline

## Tips
- Try different roles: SOC Analyst, CISO, Incident Responder
- Use hints when stuck
- Review sessions in Session Manager

See full documentation in `UI_INTEGRATION_COMPLETE.md`
