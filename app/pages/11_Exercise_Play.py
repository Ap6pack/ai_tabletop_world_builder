#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Streamlit Exercise Play Page - Multi-team tabletop exercise interface.

Supports team-specific views with 3-5 second polling for state updates.
Facilitators get full control panel; team members get filtered views.
"""

import os
import sys
import time

import requests
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT

POLL_INTERVAL = 4  # seconds

st.set_page_config(page_title="Exercise Play", page_icon="🎯", layout="wide")

# Initialize session state
for key, default in [
    ("exercise_id", None),
    ("team_id", None),
    ("member_id", None),
    ("display_name", None),
    ("exercise_version", 0),
    ("exercise_events", []),
    ("is_facilitator", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🎯 Multi-Team Exercise")

# --- Join Flow ---
if not st.session_state.exercise_id:
    st.warning("No active exercise. Go to Exercise Setup to create or join one.")
    if st.button("🏗️ Exercise Setup"):
        st.switch_page("pages/10_Exercise_Setup.py")
    st.stop()

if not st.session_state.member_id:
    st.markdown("### Join Exercise")
    st.markdown(f"Exercise ID: `{st.session_state.exercise_id}`")

    # Load exercise state to show available teams
    try:
        resp = requests.get(
            f"{API_BASE_URL}/exercise/{st.session_state.exercise_id}/state",
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code == 200:
            state = resp.json()
            teams = state.get("teams", [])

            display_name = st.text_input("Your Name")
            role = st.text_input("Your Role", value="SOC Analyst")
            team_options = {f"{t['name']} ({t['team_type']})": t["team_id"] for t in teams}
            selected_team = st.selectbox("Select Team", list(team_options.keys()))
            team_id = team_options[selected_team]

            if st.button("Join Exercise", type="primary", disabled=not display_name):
                payload = {
                    "display_name": display_name,
                    "role": role,
                    "team_id": team_id,
                }
                join_resp = requests.post(
                    f"{API_BASE_URL}/exercise/{st.session_state.exercise_id}/join",
                    json=payload,
                    timeout=DEFAULT_TIMEOUT,
                )
                if join_resp.status_code == 200:
                    data = join_resp.json()
                    st.session_state.member_id = data["member_id"]
                    st.session_state.team_id = data["team_id"]
                    st.session_state.display_name = display_name
                    # Check if facilitator team
                    for t in teams:
                        if t["team_id"] == team_id and t["team_type"] == "white":
                            st.session_state.is_facilitator = True
                    st.rerun()
                else:
                    st.error(f"Failed to join: {join_resp.json().get('detail', '')}")
        else:
            st.error("Could not load exercise state.")
    except requests.ConnectionError:
        st.error("API server not reachable.")
    st.stop()

# --- Active Exercise View ---
exercise_id = st.session_state.exercise_id
team_id = st.session_state.team_id


def poll_state():
    """Poll for exercise state updates."""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/exercise/{exercise_id}/state",
            params={"team_id": team_id},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
    except requests.ConnectionError:
        pass
    return None


state = poll_state()
if not state:
    st.error("Could not load exercise state.")
    st.stop()

phase = state.get("phase", "setup")
current_round = state.get("current_round", 0)

# --- Header Metrics ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    phase_colors = {
        "setup": "🟡",
        "active": "🟢",
        "paused": "🟠",
        "debrief": "🔵",
        "completed": "⚪",
    }
    st.metric("Phase", f"{phase_colors.get(phase, '')} {phase.title()}")
with col2:
    st.metric("Round", current_round)
with col3:
    team_info = state.get("team", {})
    st.metric("Team", team_info.get("name", "Unknown"))
with col4:
    st.metric("Score", team_info.get("score", 0))

st.markdown("---")

# --- Facilitator Controls ---
if st.session_state.is_facilitator:
    with st.expander("🎛️ Facilitator Controls", expanded=phase in ("setup", "paused")):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            if phase in ("setup", "paused"):
                label = "▶️ Start Exercise" if phase == "setup" else "▶️ Resume"
                if st.button(label, type="primary"):
                    resp = requests.post(
                        f"{API_BASE_URL}/exercise/{exercise_id}/advance",
                        params={"facilitator_id": team_id},
                        timeout=DEFAULT_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Failed"))
            elif phase == "active":
                if st.button("⏭️ Next Round"):
                    resp = requests.post(
                        f"{API_BASE_URL}/exercise/{exercise_id}/advance",
                        params={"facilitator_id": team_id},
                        timeout=DEFAULT_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        st.rerun()
        with fc2:
            if phase == "active" and st.button("⏸️ Pause"):
                requests.post(
                    f"{API_BASE_URL}/exercise/{exercise_id}/pause",
                    timeout=DEFAULT_TIMEOUT,
                )
                st.rerun()
        with fc3:
            if phase not in ("completed",) and st.button("🛑 End Exercise"):
                requests.post(
                    f"{API_BASE_URL}/exercise/{exercise_id}/end",
                    timeout=DEFAULT_TIMEOUT,
                )
                st.rerun()

        # Inject controls
        st.markdown("#### Fire Inject")
        ic1, ic2 = st.columns(2)
        with ic1:
            inject_title = st.text_input("Inject Title", key="inject_title")
            inject_type = st.selectbox(
                "Type",
                [
                    "news_article",
                    "social_media",
                    "regulator_call",
                    "ceo_demand",
                    "vendor_alert",
                    "media_inquiry",
                    "customer_complaint",
                    "law_enforcement",
                    "insider_threat",
                    "technical_failure",
                ],
            )
        with ic2:
            inject_content = st.text_area("Content", key="inject_content", height=100)
            inject_severity = st.selectbox("Severity", ["info", "low", "medium", "high", "critical"], index=2)

        if st.button("🔥 Fire Inject", disabled=not inject_title or not inject_content):
            payload = {
                "inject_type": inject_type,
                "title": inject_title,
                "content": inject_content,
                "severity": inject_severity,
                "target_teams": [],
                "requires_response": False,
            }
            resp = requests.post(
                f"{API_BASE_URL}/exercise/{exercise_id}/inject",
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 200:
                st.success(f"Inject fired: {inject_title}")
                st.rerun()

# --- Main Content Area ---
main_col, sidebar_col = st.columns([3, 1])

with main_col:
    # Active Injects
    active_injects = state.get("active_injects", [])
    if active_injects:
        st.markdown("### 🚨 Crisis Feed")
        for inject in reversed(active_injects):
            severity = inject.get("severity", "medium")
            sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(severity, "⚪")
            with st.container():
                st.markdown(
                    f"**{sev_icon} [{inject.get('inject_type', '').replace('_', ' ').title()}] "
                    f"{inject.get('title', '')}**"
                )
                st.markdown(inject.get("content", ""))
                if inject.get("requires_response"):
                    st.warning("⚠️ This inject requires a team response.")
                st.markdown("---")

    # Game State
    game_state = state.get("game_state")
    if game_state and phase == "active":
        st.markdown("### 🎮 Situation")

        # Incident Timeline
        timeline = game_state.get("incident_timeline", [])
        if timeline:
            st.markdown("**Recent Events:**")
            for event in timeline[-10:]:
                sev = event.get("severity", "info")
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(sev, "⚪")
                st.markdown(f"{icon} `{event.get('event_type', '')}` — {event.get('description', '')}")

        # Action Input
        st.markdown("### 💬 Submit Action")
        action_text = st.text_area(
            "What does your team do?",
            placeholder="e.g., Check SIEM logs for lateral movement indicators...",
            key="action_input",
        )
        if st.button("📤 Submit Action", type="primary", disabled=not action_text):
            payload = {
                "team_id": team_id,
                "member_id": st.session_state.member_id,
                "action": action_text,
            }
            with st.spinner("Processing action..."):
                resp = requests.post(
                    f"{API_BASE_URL}/exercise/{exercise_id}/action",
                    json=payload,
                    timeout=30,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.success("Action processed!")
                    st.markdown(f"**Result:** {result.get('narrative', '')}")
                    st.rerun()
                else:
                    st.error(f"Action failed: {resp.json().get('detail', '')}")

    elif phase == "setup":
        st.info("Waiting for facilitator to start the exercise...")
    elif phase == "paused":
        st.warning("Exercise is paused. Waiting for facilitator to resume.")
    elif phase in ("debrief", "completed"):
        st.success("Exercise complete! Review results in the After Action Review.")
        if st.button("📊 Go to AAR"):
            st.switch_page("pages/7_After_Action_Review.py")

with sidebar_col:
    # Exercise Event Log
    st.markdown("### 📋 Event Log")
    events = state.get("visible_events", [])
    if events:
        for event in reversed(events[-15:]):
            etype = event.get("event_type", "")
            icon = {
                "team_action": "💬",
                "inject": "🚨",
                "facilitator": "🎛️",
                "system": "⚙️",
                "round_change": "🔄",
            }.get(etype, "📌")
            st.markdown(f"{icon} R{event.get('round_number', 0)}: {event.get('description', '')}")
    else:
        st.info("No events yet.")

    # Team Members
    st.markdown("### 👥 Team")
    members = team_info.get("members", [])
    if members:
        for m in members:
            st.markdown(f"- **{m.get('display_name', '')}** ({m.get('role', '')})")
    else:
        st.info("No members yet.")

# Auto-refresh for active exercises
if phase in ("active", "setup", "paused"):
    time.sleep(POLL_INTERVAL)
    st.rerun()
