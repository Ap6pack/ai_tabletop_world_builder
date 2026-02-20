#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Streamlit Home Page - Main entry point for the war gaming platform.
"""
import streamlit as st
from pathlib import Path
from config import API_BASE_URL, HEALTH_CHECK_TIMEOUT, DEFAULT_TIMEOUT
import requests

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

# --- Build ---
st.markdown("### Build")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Scenario Builder**")
    st.caption("Generate custom cybersecurity scenarios tailored to your training needs.")
    if st.button("Create Scenario", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")

with col2:
    st.markdown("**Scenario Editor**")
    st.caption("Edit and refine existing scenarios with fine-grained controls.")
    if st.button("Edit Scenario", use_container_width=True):
        st.switch_page("pages/5_Scenario_Editor.py")

with col3:
    st.markdown("**Scenario Library**")
    st.caption("Browse, search, and manage your saved scenarios.")
    if st.button("Browse Library", use_container_width=True):
        st.switch_page("pages/9_Scenario_Library.py")

st.markdown("")

# --- Play ---
st.markdown("### Play")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**War Game**")
    st.caption("Start an interactive war gaming session and respond to security incidents.")
    if st.button("Start War Game", use_container_width=True):
        st.switch_page("pages/2_War_Game.py")

with col2:
    st.markdown("**Exercise Setup**")
    st.caption("Configure multi-team tabletop exercises with roles and injects.")
    if st.button("Setup Exercise", use_container_width=True):
        st.switch_page("pages/10_Exercise_Setup.py")

with col3:
    st.markdown("**Exercise Play**")
    st.caption("Run live multi-team exercises with real-time coordination.")
    if st.button("Play Exercise", use_container_width=True):
        st.switch_page("pages/11_Exercise_Play.py")

st.markdown("")

# --- Analyze ---
st.markdown("### Analyze")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Analytics**")
    st.caption("View performance dashboards, score trends, and training recommendations.")
    if st.button("View Analytics", use_container_width=True):
        st.switch_page("pages/6_Analytics.py")

with col2:
    st.markdown("**After Action Review**")
    st.caption("Analyze decisions and improve response strategies.")
    if st.button("Review Sessions", use_container_width=True):
        st.switch_page("pages/7_After_Action_Review.py")

with col3:
    st.markdown("**Executive Dashboard**")
    st.caption("Executive-level compliance and business impact reporting.")
    if st.button("Executive View", use_container_width=True):
        st.switch_page("pages/12_Executive_Dashboard.py")

st.markdown("")

# --- Admin ---
st.markdown("### Admin")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Settings**")
    st.caption("Configure LLM providers, content policies, and platform settings.")
    if st.button("Open Settings", use_container_width=True):
        st.switch_page("pages/3_Settings.py")

with col2:
    st.markdown("**Session Manager**")
    st.caption("View, resume, and manage past war gaming sessions.")
    if st.button("Manage Sessions", use_container_width=True):
        st.switch_page("pages/4_Session_Manager.py")

with col3:
    st.markdown("**Login**")
    st.caption("Authenticate and manage user access.")
    if st.button("Login", use_container_width=True):
        st.switch_page("pages/8_Login.py")

st.markdown("---")

# System status
st.markdown("### System Status")

col1, col2, col3 = st.columns(3)

with col1:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        if response.status_code == 200:
            st.metric("API Status", "✅ Running", delta="Ready")
        else:
            st.metric("API Status", "⚠️ Issues", delta="Check logs")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.metric("API Status", "❌ Offline", delta="Start server")
    except Exception as e:
        st.metric("API Status", "❌ Error", delta=str(e)[:20])

with col2:
    try:
        response = requests.get(f"{API_BASE_URL}/llm/providers", timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            providers = response.json()
            configured = [p for p, is_available in providers.items() if is_available]

            if configured:
                st.metric("LLM Providers", f"✅ {len(configured)} Configured")
                st.caption(", ".join(configured))
            else:
                st.metric("LLM Providers", "⚠️ None Configured")
                st.caption("Add API keys in Settings")
        else:
            st.metric("LLM Providers", f"❌ Error {response.status_code}")
    except requests.exceptions.Timeout:
        st.metric("LLM Providers", "⏱️ Timeout")
        st.caption(f"Check took >{DEFAULT_TIMEOUT}s")
    except requests.exceptions.ConnectionError:
        st.metric("LLM Providers", "❌ API Offline")
    except Exception as e:
        st.metric("LLM Providers", "❌ Error")
        st.caption(str(e)[:50])

with col3:
    try:
        response = requests.get(f"{API_BASE_URL}/scenarios/list", timeout=HEALTH_CHECK_TIMEOUT)
        if response.status_code == 200:
            count = len(response.json())
            st.metric("Saved Scenarios", count)
        else:
            st.metric("Saved Scenarios", "0", delta="API error")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.metric("Saved Scenarios", "0", delta="API offline")
    except Exception as e:
        st.metric("Saved Scenarios", "0", delta="Error")

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

    Version: 1.0.0
    Status: Phase 10 Complete
    """)
