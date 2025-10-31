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
    st.markdown("### Settings")
    st.markdown("""
    Configure LLM providers, content
    policies, and platform settings.
    """)
    if st.button("Open Settings", use_container_width=True):
        st.switch_page("pages/3_Settings.py")

st.markdown("---")

# System status
st.markdown("### System Status")

# Check if API is running
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("API Status", "Running", delta="Ready")

with col2:
    st.metric("LLM Provider", st.session_state.get("llm_provider", "Not Configured"))

with col3:
    st.metric("Content Policy", st.session_state.get("content_policy", "Educational"))

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

    Version: 0.1.0
    """)
