#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Streamlit Exercise Setup Page - Configure multi-team tabletop exercises.
"""

import os
import sys

import requests
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT, LONG_OPERATION_TIMEOUT

st.set_page_config(page_title="Exercise Setup", page_icon="🏗️", layout="wide")

# Initialize session state
if "exercise_id" not in st.session_state:
    st.session_state.exercise_id = None
if "exercise_state" not in st.session_state:
    st.session_state.exercise_state = None

st.title("🏗️ Multi-Team Exercise Setup")
st.markdown("Configure and launch collaborative tabletop exercises")
st.markdown("---")

# Check for active exercise
if st.session_state.exercise_id:
    st.success(f"Active exercise: **{st.session_state.exercise_state.get('name', 'Unknown')}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Go to Exercise", type="primary", use_container_width=True):
            st.switch_page("pages/11_Exercise_Play.py")
    with col2:
        if st.button("🆕 New Exercise", use_container_width=True):
            st.session_state.exercise_id = None
            st.session_state.exercise_state = None
            st.rerun()
    st.stop()

# --- Create New Exercise ---
st.markdown("### Exercise Configuration")

col1, col2 = st.columns(2)
with col1:
    exercise_name = st.text_input("Exercise Name", value="Incident Response Tabletop")
    exercise_desc = st.text_area(
        "Description",
        value="Multi-team cybersecurity incident response exercise",
        height=80,
    )

with col2:
    scenario_type = st.selectbox(
        "Scenario Type",
        ["incident-response", "threat-hunting", "vulnerability-management", "compliance-audit"],
    )
    difficulty = st.selectbox("Difficulty", ["beginner", "intermediate", "advanced", "expert"], index=1)

# Scenario selection
st.markdown("### Scenario")
try:
    resp = requests.get(f"{API_BASE_URL}/scenarios/list", timeout=DEFAULT_TIMEOUT)
    if resp.status_code == 200:
        scenarios = resp.json()
        if scenarios:
            scenario_names = [s.get("filename", s.get("name", "")) for s in scenarios]
            selected_scenario = st.selectbox("Select Scenario", scenario_names)
        else:
            st.info("No saved scenarios. Generate one in the Scenario Builder first.")
            selected_scenario = None
    else:
        st.warning("Could not load scenarios from API.")
        selected_scenario = None
except requests.ConnectionError:
    st.error("API server not reachable. Start the backend first.")
    selected_scenario = None

# Team configuration
st.markdown("### Team Configuration")

num_teams = st.slider("Number of Teams", 2, 6, 3)
teams = []
team_cols = st.columns(min(num_teams, 3))

team_types = ["blue", "red", "white", "executive", "custom"]
default_team_names = [
    "Blue Team (Defenders)",
    "Red Team (Attackers)",
    "White Team (Facilitators)",
    "Executive Cell",
    "Legal Team",
    "PR/Comms Team",
]
default_roles = {
    "blue": ["SOC Analyst", "Incident Responder", "Security Engineer", "CISO"],
    "red": ["Red Team Lead", "Penetration Tester", "Social Engineer"],
    "white": ["Exercise Director", "Observer", "Evaluator"],
    "executive": ["CEO", "CIO", "General Counsel", "CFO"],
    "custom": ["Team Lead", "Analyst"],
}

for i in range(num_teams):
    col_idx = i % len(team_cols)
    with team_cols[col_idx], st.expander(f"Team {i + 1}", expanded=i < 3):
        name = st.text_input(
            "Name",
            value=default_team_names[i] if i < len(default_team_names) else f"Team {i + 1}",
            key=f"team_name_{i}",
        )
        ttype = st.selectbox(
            "Type",
            team_types,
            index=min(i, len(team_types) - 1),
            key=f"team_type_{i}",
        )
        roles = st.multiselect(
            "Roles",
            default_roles.get(ttype, default_roles["custom"]),
            default=default_roles.get(ttype, default_roles["custom"])[:2],
            key=f"team_roles_{i}",
        )
        teams.append({"name": name, "team_type": ttype, "roles": roles})

# Round settings
st.markdown("### Round Settings")
col1, col2 = st.columns(2)
with col1:
    max_rounds = st.number_input("Max Rounds (0 = unlimited)", 0, 20, 5)
with col2:
    round_time = st.number_input("Round Time Limit (minutes, 0 = none)", 0, 120, 15)

# Launch
st.markdown("---")
if st.button("🚀 Launch Exercise", type="primary", use_container_width=True, disabled=not selected_scenario):
    with st.spinner("Creating exercise..."):
        payload = {
            "name": exercise_name,
            "description": exercise_desc,
            "scenario_filename": selected_scenario,
            "scenario_type": scenario_type,
            "difficulty": difficulty,
            "teams": teams,
            "max_rounds": max_rounds if max_rounds > 0 else None,
            "round_time_limit_minutes": round_time if round_time > 0 else None,
        }
        try:
            resp = requests.post(
                f"{API_BASE_URL}/exercise/create",
                json=payload,
                timeout=LONG_OPERATION_TIMEOUT,
            )
            if resp.status_code == 201:
                data = resp.json()
                st.session_state.exercise_id = data["exercise_id"]
                st.session_state.exercise_state = data
                st.success(f"Exercise created! ID: `{data['exercise_id']}`")
                st.markdown("**Teams created:**")
                for team in data.get("teams", []):
                    st.markdown(f"- **{team['name']}** ({team['type']}) — ID: `{team['team_id']}`")
                st.info("Share team IDs with participants so they can join.")
                if st.button("▶️ Go to Exercise Play"):
                    st.switch_page("pages/11_Exercise_Play.py")
            else:
                st.error(f"Failed to create exercise: {resp.json().get('detail', resp.text)}")
        except requests.ConnectionError:
            st.error("Could not connect to API server.")

# Existing exercises
st.markdown("---")
st.markdown("### Existing Exercises")
try:
    resp = requests.get(f"{API_BASE_URL}/exercise/list", timeout=DEFAULT_TIMEOUT)
    if resp.status_code == 200:
        exercises = resp.json().get("exercises", [])
        if exercises:
            for ex in exercises:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"**{ex.get('name', 'Unknown')}**")
                with col2:
                    st.write(ex.get("phase", ""))
                with col3:
                    st.write(f"Round {ex.get('current_round', 0)}")
                with col4:
                    if st.button("Join", key=f"join_{ex['exercise_id']}"):
                        st.session_state.exercise_id = ex["exercise_id"]
                        st.session_state.exercise_state = ex
                        st.switch_page("pages/11_Exercise_Play.py")
        else:
            st.info("No exercises found. Create one above.")
except requests.ConnectionError:
    st.warning("Could not connect to API.")
