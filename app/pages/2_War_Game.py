"""
Streamlit War Game Page - Interactive cybersecurity incident response.
"""
import streamlit as st
import requests
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import PLAYER_ROLES_DISPLAY, DIFFICULTY_LEVELS_DISPLAY

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="War Game",
    page_icon="🎮",
    layout="wide"
)

# Initialize session state
if "game_session_id" not in st.session_state:
    st.session_state.game_session_id = None
if "game_active" not in st.session_state:
    st.session_state.game_active = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "game_state" not in st.session_state:
    st.session_state.game_state = None

st.title("🎮 Cybersecurity War Game")
st.markdown("Interactive incident response training")
st.markdown("---")

# Check if scenario is loaded
if "active_scenario" not in st.session_state or not st.session_state.active_scenario:
    st.warning("⚠️ No scenario loaded. Please generate or load a scenario first.")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📋 Go to Scenario Builder", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Scenario_Builder.py")
else:
    scenario = st.session_state.active_scenario
    metadata = st.session_state.get("scenario_metadata", {})

    # Game header with metrics
    if st.session_state.game_state:
        game_state = st.session_state.game_state
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Organization", game_state.get("organization", {}).get("name", "Unknown"))
        with col2:
            st.metric("Score", game_state.get("score", 0))
        with col3:
            st.metric("Time Elapsed", f"{game_state.get('time_elapsed', 0)} min")
        with col4:
            st.metric("Status", game_state.get("status", "Unknown").title())
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Organization", scenario.get("name", "Unknown"))
        with col2:
            role_key = metadata.get("player_role", "soc-analyst")
            st.metric("Role", PLAYER_ROLES_DISPLAY.get(role_key, role_key.replace("-", " ").title()))
        with col3:
            diff_key = metadata.get("difficulty", "intermediate")
            st.metric("Difficulty", DIFFICULTY_LEVELS_DISPLAY.get(diff_key, diff_key.capitalize()))

    st.markdown("---")

    # Main game area with sidebar
    col_main, col_sidebar = st.columns([2, 1])

    with col_main:
        st.markdown("### 💬 Incident Console")

        # Chat interface
        chat_container = st.container(height=400, border=True)

        with chat_container:
            if not st.session_state.game_active:
                st.info("🎯 Click **'Start Incident'** below to begin the war game scenario.")
            else:
                # Display chat history
                if not st.session_state.chat_history:
                    st.info("Waiting for game to start...")
                else:
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

                # Process action via API
                with st.spinner("🤖 Processing your action..."):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/game/action",
                            json={
                                "session_id": st.session_state.game_session_id,
                                "action": user_action
                            },
                            timeout=30
                        )

                        if response.status_code == 200:
                            result = response.json()
                            narrative = result.get("narrative", "No response from game master.")

                            # Update game state
                            st.session_state.game_state = result.get("game_state")

                            # Add AI response to chat
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": narrative
                            })

                        else:
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": f"❌ Error processing action: {response.status_code}"
                            })

                    except Exception as e:
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": f"❌ Error: {str(e)}"
                        })

                st.rerun()

        # Game controls
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if not st.session_state.game_active:
                if st.button("▶️ Start Incident", use_container_width=True, type="primary"):
                    # Start game via API
                    with st.spinner("🎬 Starting incident scenario..."):
                        try:
                            # Determine scenario filename from loaded scenario
                            scenario_filename = None

                            # Try to get from saved scenarios list
                            try:
                                list_response = requests.get(f"{API_BASE_URL}/scenarios/list", timeout=5)
                                if list_response.status_code == 200:
                                    scenarios = list_response.json()
                                    # Find matching scenario by name
                                    for s in scenarios:
                                        if s['name'] == scenario.get('name'):
                                            scenario_filename = s['filename']
                                            break
                            except:
                                pass

                            if not scenario_filename:
                                st.error("❌ Could not determine scenario filename. Please reload the scenario.")
                            else:
                                response = requests.post(
                                    f"{API_BASE_URL}/game/start",
                                    json={
                                        "scenario_filename": scenario_filename,
                                        "scenario_type": metadata.get("scenario_type", "incident-response").lower().replace(" ", "-"),
                                        "player_role": metadata.get("player_role", "soc-analyst"),
                                        "difficulty": metadata.get("difficulty", "intermediate")
                                    },
                                    timeout=30
                                )

                                if response.status_code == 200:
                                    result = response.json()
                                    st.session_state.game_session_id = result["game_state"]["session_id"]
                                    st.session_state.game_state = result["game_state"]
                                    st.session_state.game_active = True

                                    # Add opening narrative to chat
                                    st.session_state.chat_history = [{
                                        "role": "assistant",
                                        "content": result.get("narrative", "Game started!")
                                    }]

                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to start game: {response.status_code}")
                                    try:
                                        error_detail = response.json()
                                        st.error(f"Details: {error_detail.get('detail', 'Unknown error')}")
                                    except:
                                        st.error(f"Response: {response.text[:500]}")

                        except Exception as e:
                            st.error(f"❌ Error starting game: {str(e)}")

        with col2:
            if st.session_state.game_active:
                if st.button("💡 Get Hint", use_container_width=True):
                    with st.spinner("💭 Generating hint..."):
                        try:
                            response = requests.post(
                                f"{API_BASE_URL}/game/hint",
                                params={"session_id": st.session_state.game_session_id},
                                timeout=15
                            )

                            if response.status_code == 200:
                                hint = response.json().get("hint", "No hint available")
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": f"💡 **Hint:** {hint}"
                                })
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error getting hint: {str(e)}")

        with col3:
            if st.session_state.game_active:
                if st.button("💾 Save Progress", use_container_width=True):
                    st.success("✅ Progress auto-saved")

        with col4:
            if st.session_state.game_active:
                if st.button("🛑 End Game", use_container_width=True):
                    with st.spinner("Ending game..."):
                        try:
                            response = requests.post(
                                f"{API_BASE_URL}/game/end",
                                json={
                                    "session_id": st.session_state.game_session_id,
                                    "status": "completed"
                                },
                                timeout=5
                            )

                            if response.status_code == 200:
                                st.session_state.game_active = False
                                final_state = response.json()

                                # Show final summary
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": f"""
🎉 **Game Complete!**

**Final Score:** {final_state.get('score', 0)} points
**Time Elapsed:** {final_state.get('time_elapsed', 0)} minutes
**Status:** {final_state.get('status', 'completed').title()}

Check the After Action Review for detailed analysis.
"""
                                })
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error ending game: {str(e)}")

    with col_sidebar:
        # Game state info
        if st.session_state.game_state:
            game_state = st.session_state.game_state

            # Score and time
            st.markdown("### 📊 Game Status")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Score", game_state.get("score", 0), delta=None)
            with col2:
                st.metric("Time", f"{game_state.get('time_elapsed', 0)}m")

            # Score breakdown
            if game_state.get("score_history"):
                with st.expander("Score Breakdown"):
                    for score_event in game_state["score_history"][-5:]:  # Show last 5
                        points = score_event.get("points", 0)
                        reason = score_event.get("reason", "Unknown")
                        color = "🟢" if points > 0 else "🔴" if points < 0 else "⚪"
                        st.markdown(f"{color} **{points:+d}** - {reason}")

            st.markdown("---")

            # Incident Timeline
            st.markdown("### 📅 Incident Timeline")
            timeline_container = st.container(height=200, border=True)
            with timeline_container:
                timeline = game_state.get("incident_timeline", [])
                if timeline:
                    # Show most recent events first
                    for event in reversed(timeline[-10:]):  # Last 10 events
                        event_type = event.get("event_type", "info")
                        event_emoji = {
                            "detection": "🚨",
                            "action": "⚡",
                            "consequence": "📍",
                            "escalation": "⚠️"
                        }.get(event_type, "📌")

                        severity = event.get("severity", "info")
                        severity_color = {
                            "critical": "🔴",
                            "high": "🟠",
                            "medium": "🟡",
                            "low": "🟢",
                            "info": "⚪"
                        }.get(severity, "⚪")

                        st.markdown(f"{event_emoji} {severity_color} {event.get('description', 'Event')}")
                        st.caption(f"_{event.get('actor', 'system')}_")
                else:
                    st.info("No events yet")

            st.markdown("---")

            # Available Tools/Inventory
            st.markdown("### 🛠️ Available Tools")
            with st.expander("View Inventory", expanded=True):
                inventory = game_state.get("inventory", {})
                tools = inventory.get("tools", {})

                if tools:
                    for tool_name, count in tools.items():
                        st.markdown(f"✅ {tool_name}")
                else:
                    st.info("No tools available")

                st.markdown("\n**Access Levels:**")
                access_levels = inventory.get("access_levels", [])
                if access_levels:
                    for level in access_levels:
                        st.markdown(f"🔑 {level.upper()}")
                else:
                    st.info("No access levels")

            st.markdown("---")

            # Objectives
            st.markdown("### 🎯 Objectives")
            with st.expander("View Objectives", expanded=True):
                objectives = game_state.get("objectives", [])
                if objectives:
                    for obj in objectives:
                        status = "✅" if obj.get("completed") else "⏳"
                        st.markdown(f"{status} {obj.get('description', 'Objective')}")
                else:
                    # Show generic objectives
                    st.markdown("""
                    ⏳ Investigate the incident
                    ⏳ Identify the attack vector
                    ⏳ Contain the threat
                    ⏳ Preserve evidence
                    ⏳ Document your actions
                    """)
        else:
            st.info("🎮 Start the game to see live status updates")

# Sidebar navigation
with st.sidebar:
    st.markdown("## Game Sessions")

    # List active sessions
    try:
        response = requests.get(f"{API_BASE_URL}/game/sessions", timeout=5)
        if response.status_code == 200:
            sessions = response.json().get("sessions", [])

            if sessions:
                st.markdown(f"**Active Sessions:** {len(sessions)}")

                for session in sessions[:5]:  # Show first 5
                    with st.expander(f"{session['organization'][:20]}..."):
                        st.markdown(f"**Role:** {session['player_role']}")
                        st.markdown(f"**Status:** {session['status']}")
                        st.markdown(f"**Score:** {session['score']}")

                        if st.button("Load Session", key=f"load_{session['session_id'][:8]}"):
                            st.session_state.game_session_id = session['session_id']
                            # Load game state
                            try:
                                state_response = requests.get(
                                    f"{API_BASE_URL}/game/state/{session['session_id']}",
                                    timeout=5
                                )
                                if state_response.status_code == 200:
                                    game_data = state_response.json()
                                    st.session_state.game_state = game_data
                                    st.session_state.game_active = game_data.get("status") == "in_progress"

                                    # Reconstruct chat history from timeline
                                    st.session_state.chat_history = []
                                    timeline = game_data.get("incident_timeline", [])
                                    for event in timeline:
                                        if event.get("event_type") == "action":
                                            st.session_state.chat_history.append({
                                                "role": "user",
                                                "content": event.get("description", "")
                                            })
                                        elif event.get("event_type") in ["detection", "consequence"]:
                                            st.session_state.chat_history.append({
                                                "role": "assistant",
                                                "content": event.get("description", "")
                                            })

                                    # Load scenario
                                    org_name = game_data.get("organization", {}).get("name")
                                    if org_name:
                                        st.session_state.active_scenario = game_data.get("organization", {})

                                    st.success("✅ Session loaded!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error loading session: {str(e)}")
            else:
                st.info("No active sessions")
    except Exception as e:
        st.warning("Could not load sessions")

    st.markdown("---")

    st.markdown("## Quick Actions")

    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")

    if st.button("📋 New Scenario", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")

    st.markdown("---")

    st.markdown("## Tips")
    with st.expander("Response Best Practices"):
        st.markdown("""
        1. **Assess** the situation first
        2. **Contain** before investigating
        3. **Document** all actions
        4. **Communicate** with team
        5. **Preserve** evidence

        **Good Actions:**
        - Check logs and alerts
        - Isolate affected systems
        - Gather evidence
        - Escalate when needed

        **Avoid:**
        - Rash decisions
        - Destroying evidence
        - Exceeding your access
        - Ignoring procedures
        """)
