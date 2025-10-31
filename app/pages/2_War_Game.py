"""
Streamlit War Game Page - Interactive cybersecurity incident response.
"""
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="War Game",
    page_icon="",
    layout="wide"
)

# Initialize session state
if "game_active" not in st.session_state:
    st.session_state.game_active = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "game_state" not in st.session_state:
    st.session_state.game_state = None
if "incident_timeline" not in st.session_state:
    st.session_state.incident_timeline = []

st.title("🎮 Cybersecurity War Game")
st.markdown("Interactive incident response training")
st.markdown("---")

# Check if scenario is loaded
if "active_scenario" not in st.session_state:
    st.warning("No scenario loaded. Please generate a scenario first.")
    if st.button("Go to Scenario Builder"):
        st.switch_page("pages/1_Scenario_Builder.py")
else:
    # Scenario info
    scenario = st.session_state.active_scenario
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Organization", scenario.get("name", "Unknown"))
    with col2:
        st.metric("Scenario", scenario.get("scenario_type", "Incident Response"))
    with col3:
        st.metric("Difficulty", scenario.get("difficulty", "intermediate").capitalize())
    with col4:
        st.metric("Time Elapsed", "0 min")

    st.markdown("---")

    # Main game area with sidebar
    col_main, col_sidebar = st.columns([2, 1])

    with col_main:
        st.markdown("### 💬 Incident Console")

        # Chat interface
        chat_container = st.container(height=400)

        with chat_container:
            if not st.session_state.game_active:
                st.info("Click 'Start Incident' to begin the war game scenario.")
            else:
                # Display chat history
                for message in st.session_state.chat_history:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

        # User input
        if st.session_state.game_active:
            user_action = st.chat_input("Enter your action (e.g., 'Check SIEM logs for suspicious activity')")

            if user_action:
                # Add user message to chat
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_action
                })

                # TODO: Send to API for processing
                # Placeholder AI response
                ai_response = "🤖 Processing your action..."
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": ai_response
                })

                st.rerun()

        # Game controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if not st.session_state.game_active:
                if st.button("▶️ Start Incident", use_container_width=True, type="primary"):
                    st.session_state.game_active = True
                    st.session_state.chat_history = [{
                        "role": "assistant",
                        "content": """🚨 **SECURITY ALERT**

You are a SOC Analyst at Example Financial Services Corp.

**Initial Alert:**
- Time: 09:45 AM
- Source: EDR System
- Severity: HIGH
- Description: Suspicious PowerShell execution detected on workstation FIN-WS-042

**Your Objectives:**
1. Investigate the alert
2. Determine if this is a real threat
3. Contain any malicious activity
4. Preserve evidence
5. Escalate if necessary

What is your first action?"""
                    }]
                    st.rerun()
        with col2:
            if st.session_state.game_active:
                if st.button("⏸️ Pause Game", use_container_width=True):
                    st.info("Game paused")
        with col3:
            if st.session_state.game_active:
                if st.button("🛑 End Game", use_container_width=True):
                    st.session_state.game_active = False
                    st.success("Game ended. Check After Action Review for analysis.")

    with col_sidebar:
        # Incident Timeline
        st.markdown("### 📅 Incident Timeline")
        timeline_container = st.container(height=200)
        with timeline_container:
            if st.session_state.incident_timeline:
                for event in st.session_state.incident_timeline:
                    st.markdown(f"**{event['time']}** - {event['description']}")
            else:
                st.info("No events yet")

        st.markdown("---")

        # Available Tools/Inventory
        st.markdown("### 🛠️ Available Tools")
        with st.expander("View Inventory", expanded=True):
            st.markdown("""
            **Detection:**
            - SIEM (Splunk)
            - EDR (CrowdStrike)
            - IDS/IPS

            **Analysis:**
            - Wireshark
            - Memory Forensics
            - Log Parser

            **Response:**
            - Firewall Rules
            - EDR Isolation
            - Active Directory
            """)

        st.markdown("---")

        # Objectives
        st.markdown("### 🎯 Current Objectives")
        with st.expander("View Objectives", expanded=True):
            st.markdown("""
            - [ ] Investigate initial alert
            - [ ] Identify attack vector
            - [ ] Contain threat
            - [ ] Preserve evidence
            - [ ] Document actions
            """)

        st.markdown("---")

        # Hints
        if st.button("💡 Get Hint", use_container_width=True):
            st.info("Check the SIEM for related events around the alert time.")

# Sidebar navigation
with st.sidebar:
    st.markdown("## Game Options")

    content_policy = st.selectbox(
        "Content Policy",
        ["Defensive", "Educational", "Advanced", "Unrestricted"]
    )

    st.markdown("---")

    st.markdown("## Quick Actions")
    if st.button("📊 View Dashboard", use_container_width=True):
        st.info("Dashboard coming soon")

    if st.button("💾 Save Progress", use_container_width=True):
        st.success("Progress saved")

    if st.button("📝 Export Log", use_container_width=True):
        st.info("Log export coming soon")

    st.markdown("---")

    st.markdown("## Tips")
    with st.expander("Response Best Practices"):
        st.markdown("""
        1. **Assess** the situation first
        2. **Contain** before investigating
        3. **Document** all actions
        4. **Communicate** with team
        5. **Preserve** evidence
        """)
