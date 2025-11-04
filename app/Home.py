"""
Streamlit Home Page - Main entry point for the war gaming platform.
"""
import streamlit as st
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Cybersecurity War Gaming Platform",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main title
st.title("Cybersecurity War Gaming Platform")
st.markdown("---")

# Welcome section
st.markdown("""
### Welcome to the AI-Powered Cybersecurity Training Platform

This platform provides realistic, AI-generated cybersecurity scenarios for training security teams
in incident response, threat detection, and defensive security operations.

#### Key Features

- **Hierarchical Scenario Generation**: Create realistic organizations with complete IT infrastructure
- **Interactive War Gaming**: Respond to live security incidents with AI-powered threat simulation
- **Real-time Dashboards**: Monitor team performance and incident timelines
- **Configurable Content Policies**: Adjust scenario realism from defensive-only to advanced training
- **After Action Reviews**: Analyze decisions and improve response strategies

#### Getting Started

1. **Configure LLM Provider** → Set up your AI provider (OpenAI, Anthropic, or local Ollama)
2. **Generate Scenario** → Create a custom cybersecurity training scenario
3. **Start War Game** → Begin interactive incident response training
4. **Review Performance** → Analyze your decisions and learn from the experience
""")

st.markdown("---")

# Show tutorial for first-time users
if "hide_tutorial" not in st.session_state:
    st.session_state.hide_tutorial = False

if not st.session_state.hide_tutorial:
    with st.container(border=True):
        st.markdown("### 👋 Welcome to the Cybersecurity War Gaming Platform!")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("""
            This platform helps you practice incident response through AI-powered simulations:

            1. **Generate Scenarios** - Create realistic cybersecurity incidents
            2. **Play War Games** - Make decisions and respond to threats
            3. **Learn & Improve** - Review your performance and learn from mistakes

            **Quick Start:** Click "Create Scenario" below to begin!
            """)
        with col2:
            if st.button("✖️ Hide Tutorial", use_container_width=True):
                st.session_state.hide_tutorial = True
                st.rerun()

st.markdown("---")

# Quick start section
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Scenario Builder")
    st.markdown("""
    Generate custom cybersecurity
    scenarios tailored to your
    training needs.
    """)
    if st.button("Create Scenario", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")

with col2:
    st.markdown("### 🎮 War Game")
    st.markdown("""
    Start an interactive war gaming
    session and respond to security
    incidents.
    """)
    if st.button("Start War Game", use_container_width=True):
        st.switch_page("pages/2_War_Game.py")

with col3:
    st.markdown("### 📊 Session Manager")
    st.markdown("""
    View and manage your war gaming
    sessions, scores, and history.
    """)
    if st.button("View Sessions", use_container_width=True):
        st.switch_page("pages/3_Session_Manager.py")

st.markdown("---")

# System status
st.markdown("### System Status")

# Check if API is running
import requests

col1, col2, col3 = st.columns(3)

with col1:
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if response.status_code == 200:
            st.metric("API Status", "✅ Running", delta="Ready")
        else:
            st.metric("API Status", "⚠️ Issues", delta="Check logs")
    except:
        st.metric("API Status", "❌ Offline", delta="Start server")

with col2:
    try:
        response = requests.get("http://127.0.0.1:8000/llm/providers", timeout=2)
        if response.status_code == 200:
            providers = response.json()
            # API returns {"openai": true, "anthropic": false, ...}
            available = [p for p, is_available in providers.items() if is_available]
            if available:
                st.metric("LLM Providers", f"✅ {len(available)} Active")
                st.caption(", ".join(available))
            else:
                st.metric("LLM Providers", "⚠️ None Configured")
                st.caption("Check .env file")
        else:
            st.metric("LLM Providers", "Unknown")
    except Exception as e:
        st.metric("LLM Providers", "Unable to check")

with col3:
    # Get scenarios count
    try:
        response = requests.get("http://127.0.0.1:8000/scenarios/list", timeout=2)
        if response.status_code == 200:
            count = len(response.json())
            st.metric("Saved Scenarios", count)
        else:
            st.metric("Saved Scenarios", "0")
    except:
        st.metric("Saved Scenarios", "0")

# Sidebar
with st.sidebar:
    st.markdown("## Navigation")
    st.markdown("""
    Use the pages above to:
    - Build scenarios
    - Run war games
    - Configure settings
    - Review past sessions
    """)

    st.markdown("---")
    st.markdown("### About")
    st.info("""
    **Cybersecurity War Gaming Platform**

    An AI-powered training platform
    for security teams to practice
    incident response and defensive
    security operations.

    Version: 0.3.0
    Status: Phase 2 & 3 Complete
    """)
