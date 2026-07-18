#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Streamlit Session Manager Page - View and manage game sessions.
"""

import requests
import streamlit as st

from config import API_BASE_URL, DEFAULT_TIMEOUT

st.set_page_config(page_title="Session Manager", page_icon="📊", layout="wide")

st.title("📊 Session Manager")
st.markdown("View and manage your war gaming sessions")
st.markdown("---")

# Fetch sessions
try:
    response = requests.get(f"{API_BASE_URL}/game/sessions", timeout=DEFAULT_TIMEOUT)

    if response.status_code == 200:
        data = response.json()
        sessions = data.get("sessions", [])

        if not sessions:
            st.info("🎮 No game sessions yet. Start a war game to create your first session!")
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("📋 Go to Scenario Builder", use_container_width=True, type="primary"):
                    st.switch_page("pages/1_Scenario_Builder.py")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            in_progress = [s for s in sessions if s.get("status") == "in_progress"]
            completed = [s for s in sessions if s.get("status") == "completed"]
            avg_score = sum(s.get("score", 0) for s in completed) / len(completed) if completed else 0

            with col1:
                st.metric("Total Sessions", len(sessions))
            with col2:
                st.metric("In Progress", len(in_progress))
            with col3:
                st.metric("Completed", len(completed))
            with col4:
                st.metric("Avg Score", f"{avg_score:.0f}")

            st.markdown("---")

            # Filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_status = st.selectbox("Filter by Status", ["All", "In Progress", "Completed", "Failed"])
            with col2:
                filter_role = st.selectbox(
                    "Filter by Role", ["All"] + list(set(s.get("player_role", "unknown") for s in sessions))
                )
            with col3:
                sort_by = st.selectbox("Sort by", ["Most Recent", "Highest Score", "Lowest Score", "Duration"])

            # Apply filters
            filtered_sessions = sessions

            if filter_status != "All":
                status_map = {"In Progress": "in_progress", "Completed": "completed", "Failed": "failed"}
                filtered_sessions = [s for s in filtered_sessions if s.get("status") == status_map[filter_status]]

            if filter_role != "All":
                filtered_sessions = [s for s in filtered_sessions if s.get("player_role") == filter_role]

            # Sort
            if sort_by == "Highest Score":
                filtered_sessions.sort(key=lambda s: s.get("score", 0), reverse=True)
            elif sort_by == "Lowest Score":
                filtered_sessions.sort(key=lambda s: s.get("score", 0))
            elif sort_by == "Duration":
                filtered_sessions.sort(key=lambda s: s.get("time_elapsed", 0), reverse=True)
            else:  # Most Recent
                filtered_sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)

            st.markdown(f"### Sessions ({len(filtered_sessions)})")

            # Display sessions as cards
            for session in filtered_sessions:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                    with col1:
                        st.markdown(f"### {session.get('organization', 'Unknown Org')[:40]}")
                        st.caption(f"Session ID: {session.get('session_id', 'unknown')[:16]}...")

                        # Status badge
                        status = session.get("status", "unknown")
                        status_emoji = {"in_progress": "🟢", "completed": "✅", "failed": "❌"}.get(status, "⚪")
                        st.markdown(f"{status_emoji} **{status.replace('_', ' ').title()}**")

                    with col2:
                        st.metric("Score", session.get("score", 0))
                        st.metric("Role", session.get("player_role", "unknown").replace("-", " ").title())

                    with col3:
                        st.metric("Duration", f"{session.get('time_elapsed', 0)} min")
                        st.metric("Actions", len(session.get("incident_timeline", [])))

                    with col4:
                        st.markdown("**Actions:**")

                        # Load session button
                        if st.button("📂 Load", key=f"load_{session['session_id']}", use_container_width=True):
                            # Store session ID and switch to war game page
                            st.session_state.game_session_id = session["session_id"]

                            # Load full state
                            try:
                                state_response = requests.get(
                                    f"{API_BASE_URL}/game/state/{session['session_id']}", timeout=DEFAULT_TIMEOUT
                                )
                                if state_response.status_code == 200:
                                    game_data = state_response.json()
                                    st.session_state.game_state = game_data
                                    st.session_state.game_active = game_data.get("status") == "in_progress"

                                    # Reconstruct chat history
                                    st.session_state.chat_history = []
                                    timeline = game_data.get("incident_timeline", [])
                                    for event in timeline:
                                        if event.get("event_type") == "action":
                                            st.session_state.chat_history.append(
                                                {"role": "user", "content": event.get("description", "")}
                                            )
                                        elif event.get("event_type") in ["detection", "consequence"]:
                                            st.session_state.chat_history.append(
                                                {"role": "assistant", "content": event.get("description", "")}
                                            )

                                    # Load scenario
                                    st.session_state.active_scenario = game_data.get("organization", {})

                                    st.switch_page("pages/2_War_Game.py")
                            except Exception as e:
                                st.error(f"Error loading session: {str(e)}")

                        # View details
                        if st.button("📊 Details", key=f"details_{session['session_id']}", use_container_width=True):
                            st.session_state.selected_session_id = session["session_id"]
                            st.rerun()

                        # Delete session - allow for any status
                        if st.button("🗑️ Delete", key=f"delete_{session['session_id']}", use_container_width=True):
                            try:
                                delete_response = requests.delete(
                                    f"{API_BASE_URL}/game/sessions/{session['session_id']}", timeout=DEFAULT_TIMEOUT
                                )
                                if delete_response.status_code == 200:
                                    st.success("✅ Session deleted")
                                    st.rerun()
                                else:
                                    error_msg = delete_response.json().get("detail", "Unknown error")
                                    st.error(f"Failed to delete: {error_msg}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                    # Show details if selected
                    if st.session_state.get("selected_session_id") == session.get("session_id"):
                        st.markdown("---")
                        st.markdown("### 📋 Session Details")

                        # Get full session state
                        try:
                            state_response = requests.get(
                                f"{API_BASE_URL}/game/state/{session['session_id']}", timeout=DEFAULT_TIMEOUT
                            )
                            if state_response.status_code == 200:
                                full_state = state_response.json()

                                tab1, tab2, tab3 = st.tabs(["Timeline", "Objectives", "Inventory"])

                                with tab1:
                                    timeline = full_state.get("incident_timeline", [])
                                    st.markdown(f"**Total Events:** {len(timeline)}")

                                    for event in reversed(timeline):
                                        event_type = event.get("event_type", "info")
                                        event_emoji = {
                                            "detection": "🚨",
                                            "action": "⚡",
                                            "consequence": "📍",
                                            "escalation": "⚠️",
                                        }.get(event_type, "📌")

                                        severity = event.get("severity", "info")
                                        severity_color = {
                                            "critical": "🔴",
                                            "high": "🟠",
                                            "medium": "🟡",
                                            "low": "🟢",
                                            "info": "⚪",
                                        }.get(severity, "⚪")

                                        st.markdown(
                                            f"{event_emoji} {severity_color} {event.get('description', 'Event')}"
                                        )
                                        st.caption(f"_{event.get('actor', 'system')} - {event.get('timestamp', '')}s_")

                                with tab2:
                                    objectives = full_state.get("objectives", [])
                                    if objectives:
                                        for obj in objectives:
                                            status = "✅" if obj.get("completed") else "⏳"
                                            st.markdown(f"{status} {obj.get('description', 'Objective')}")
                                    else:
                                        st.info("No specific objectives set")

                                with tab3:
                                    inventory = full_state.get("inventory", {})

                                    st.markdown("**Tools:**")
                                    tools = inventory.get("tools", {})
                                    if tools:
                                        for tool_name in tools:
                                            st.markdown(f"✅ {tool_name}")
                                    else:
                                        st.info("No tools")

                                    st.markdown("\n**Access Levels:**")
                                    access_levels = inventory.get("access_levels", [])
                                    if access_levels:
                                        for level in access_levels:
                                            st.markdown(f"🔑 {level.upper()}")
                                    else:
                                        st.info("No access levels")

                                    credentials = inventory.get("credentials", {})
                                    if credentials:
                                        st.markdown("\n**Credentials:**")
                                        for cred_type, creds in credentials.items():
                                            st.markdown(f"🔐 {cred_type}: {len(creds)} accounts")

                        except Exception as e:
                            st.error(f"Could not load session details: {str(e)}")

                        if st.button("✖️ Close Details", key=f"close_{session['session_id']}"):
                            st.session_state.selected_session_id = None
                            st.rerun()
    else:
        st.error(f"Failed to fetch sessions: {response.status_code}")

except requests.exceptions.ConnectionError:
    st.error(f"🔌 Could not connect to API. Make sure the backend is running on {API_BASE_URL}")
except Exception as e:
    st.error(f"❌ Error: {str(e)}")

# Sidebar
with st.sidebar:
    st.markdown("## Navigation")

    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")

    if st.button("📋 Scenario Builder", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")

    if st.button("🎮 War Game", use_container_width=True):
        st.switch_page("pages/2_War_Game.py")

    st.markdown("---")

    st.markdown("## Quick Stats")
    try:
        response = requests.get(f"{API_BASE_URL}/game/sessions", timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            sessions = response.json().get("sessions", [])

            total_time = sum(s.get("time_elapsed", 0) for s in sessions)
            total_actions = sum(len(s.get("incident_timeline", [])) for s in sessions)

            st.metric("Total Play Time", f"{total_time} min")
            st.metric("Total Actions", total_actions)
    except requests.exceptions.RequestException:
        st.info("Stats unavailable")
