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
from config import API_BASE_URL, DEFAULT_TIMEOUT, LONG_OPERATION_TIMEOUT

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

# Check if scenario is loaded OR if we have an active game session
has_scenario = st.session_state.get("active_scenario") is not None
has_game_session = st.session_state.get("game_state") is not None

if not has_scenario and not has_game_session:
    st.warning("⚠️ No scenario or game session loaded. Please generate a scenario or load an existing session.")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("📋 Scenario Builder", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Scenario_Builder.py")
    with col3:
        if st.button("📊 Session Manager", use_container_width=True, type="primary"):
            st.switch_page("pages/3_Session_Manager.py")
else:
    # Get scenario from either active_scenario or game_state
    scenario = st.session_state.get("active_scenario")
    if not scenario and st.session_state.get("game_state"):
        scenario = st.session_state.game_state.get("organization", {})

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
                            timeout=LONG_OPERATION_TIMEOUT
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
                                list_response = requests.get(f"{API_BASE_URL}/scenarios/list", timeout=DEFAULT_TIMEOUT)
                                if list_response.status_code == 200:
                                    scenarios = list_response.json()
                                    # Find matching scenario by name
                                    for s in scenarios:
                                        if s['name'] == scenario.get('name'):
                                            scenario_filename = s['filename']
                                            break
                            except requests.exceptions.RequestException:
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
                                    timeout=LONG_OPERATION_TIMEOUT
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
                                    except Exception:
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
                                timeout=DEFAULT_TIMEOUT
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

            # System Status Dashboard
            st.markdown("### 🖥️ System Status")
            with st.expander("View Systems", expanded=True):
                system_states = game_state.get("system_states", {})

                if system_states:
                    # Status summary
                    status_counts = {}
                    for state in system_states.values():
                        status = state.get("status", "online")
                        status_counts[status] = status_counts.get(status, 0) + 1

                    # Display summary
                    st.markdown("**Status Summary:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        online = status_counts.get("online", 0) + status_counts.get("patched", 0)
                        st.metric("🟢 Online", online)
                    with col2:
                        at_risk = status_counts.get("compromised", 0) + status_counts.get("recovering", 0)
                        st.metric("🟡 At Risk", at_risk)
                    with col3:
                        offline = status_counts.get("offline", 0)
                        st.metric("🔴 Offline", offline)

                    st.markdown("---")

                    # Group systems by status
                    compromised = []
                    offline_systems = []
                    recovering = []
                    healthy = []

                    # Get system details from organization
                    org = game_state.get("organization", {})
                    system_lookup = {}
                    for dept in org.get("departments", []):
                        for sys in dept.get("systems", []):
                            system_lookup[sys.get("id")] = {
                                "name": sys.get("name"),
                                "type": sys.get("type"),
                                "criticality": sys.get("criticality"),
                                "department": dept.get("name")
                            }

                    # Categorize systems
                    for system_id, state in system_states.items():
                        system_info = system_lookup.get(system_id, {"name": system_id, "type": "unknown", "criticality": "medium"})
                        system_data = {**system_info, "state": state}

                        status = state.get("status", "online")
                        if status == "compromised":
                            compromised.append(system_data)
                        elif status == "offline":
                            offline_systems.append(system_data)
                        elif status == "recovering":
                            recovering.append(system_data)
                        else:
                            healthy.append(system_data)

                    # Display compromised systems first (priority)
                    if compromised:
                        st.markdown("**🔴 COMPROMISED:**")
                        for sys in compromised:
                            health = sys["state"].get("health", 100)
                            criticality_badge = {"critical": "🔥", "high": "⚠️", "medium": "📌", "low": "ℹ️"}.get(sys.get("criticality", "medium"), "📌")
                            st.markdown(f"{criticality_badge} **{sys.get('name', 'Unknown')}**")
                            st.caption(f"Health: {health}% | {sys.get('type', 'system')} | {sys.get('department', 'Unknown')}")
                            if sys["state"].get("notes"):
                                st.caption(f"_{sys['state']['notes']}_")
                        st.markdown("---")

                    # Display offline systems
                    if offline_systems:
                        st.markdown("**🔴 OFFLINE:**")
                        for sys in offline_systems:
                            st.markdown(f"⛔ {sys.get('name', 'Unknown')}")
                            st.caption(f"{sys.get('type', 'system')} | {sys.get('department', 'Unknown')}")
                        st.markdown("---")

                    # Display recovering systems
                    if recovering:
                        st.markdown("**🟡 RECOVERING:**")
                        for sys in recovering:
                            health = sys["state"].get("health", 100)
                            st.markdown(f"🔄 {sys.get('name', 'Unknown')} ({health}%)")
                            st.caption(f"{sys.get('type', 'system')}")
                        st.markdown("---")

                    # Display healthy systems (collapsed by default)
                    if healthy:
                        with st.expander(f"🟢 Healthy Systems ({len(healthy)})", expanded=False):
                            for sys in healthy:
                                health = sys["state"].get("health", 100)
                                status_icon = "✅" if sys["state"].get("status") == "patched" else "🟢"
                                st.markdown(f"{status_icon} {sys.get('name', 'Unknown')} ({health}%)")
                else:
                    st.info("System states will appear here during gameplay")

            st.markdown("---")

            # Threat Actor Status
            st.markdown("### 🎭 Threat Actors")
            with st.expander("View Threat Status", expanded=True):
                threat_states = game_state.get("threat_states", {})

                if threat_states:
                    # Status summary
                    status_counts = {}
                    for state in threat_states.values():
                        status = state.get("status", "active")
                        status_counts[status] = status_counts.get(status, 0) + 1

                    # Display summary
                    st.markdown("**Threat Summary:**")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        active = status_counts.get("active", 0)
                        st.metric("🔴 Active", active)
                    with col2:
                        contained = status_counts.get("contained", 0)
                        st.metric("🟡 Contained", contained)
                    with col3:
                        dormant = status_counts.get("dormant", 0)
                        st.metric("🔵 Dormant", dormant)
                    with col4:
                        eliminated = status_counts.get("eliminated", 0)
                        st.metric("🟢 Eliminated", eliminated)

                    st.markdown("---")

                    # Get threat actor details from organization
                    org = game_state.get("organization", {})
                    threat_lookup = {}
                    for threat in org.get("threat_actors", []):
                        threat_lookup[threat.get("id")] = {
                            "name": threat.get("name"),
                            "motivation": threat.get("motivation"),
                            "sophistication": threat.get("sophistication"),
                            "ttps": threat.get("ttps", [])
                        }

                    # Group threats by status
                    active_threats = []
                    contained_threats = []
                    other_threats = []

                    for threat_id, state in threat_states.items():
                        threat_info = threat_lookup.get(threat_id, {"name": threat_id, "motivation": "unknown", "sophistication": "unknown"})
                        threat_data = {**threat_info, "state": state}

                        status = state.get("status", "active")
                        if status == "active":
                            active_threats.append(threat_data)
                        elif status == "contained":
                            contained_threats.append(threat_data)
                        else:
                            other_threats.append(threat_data)

                    # Display active threats first (priority)
                    if active_threats:
                        st.markdown("**🔴 ACTIVE THREATS:**")
                        for threat in active_threats:
                            state = threat["state"]
                            aggression = state.get("aggression_level", 50)
                            detection = state.get("detection_level", 0)

                            # Sophistication badge
                            soph_badge = {
                                "nation-state": "🔥",
                                "organized-crime": "⚠️",
                                "hacktivist": "📢",
                                "script-kiddie": "💻"
                            }.get(threat.get("sophistication", "unknown"), "❓")

                            st.markdown(f"{soph_badge} **{threat.get('name', 'Unknown Threat')}**")

                            # Aggression bar
                            agg_color = "🔴" if aggression > 70 else "🟡" if aggression > 40 else "🟢"
                            st.caption(f"Aggression: {agg_color} {aggression}% | Detection: {detection}%")

                            # Current tactics
                            if state.get("current_tactics"):
                                tactics_str = ", ".join(state["current_tactics"][:2])
                                st.caption(f"Tactics: {tactics_str}")

                            # Compromised systems count
                            sys_count = len(state.get("systems_compromised", []))
                            if sys_count > 0:
                                st.caption(f"💀 {sys_count} systems compromised")

                            # Last action
                            if state.get("last_action"):
                                st.caption(f"_{state['last_action']}_")

                        st.markdown("---")

                    # Display contained threats
                    if contained_threats:
                        st.markdown("**🟡 CONTAINED:**")
                        for threat in contained_threats:
                            st.markdown(f"🛡️ {threat.get('name', 'Unknown')} - Partially neutralized")
                            aggression = threat["state"].get("aggression_level", 0)
                            st.caption(f"Reduced threat level: {aggression}%")
                        st.markdown("---")

                    # Display other threats (dormant/eliminated)
                    if other_threats:
                        with st.expander(f"Other Threats ({len(other_threats)})", expanded=False):
                            for threat in other_threats:
                                status = threat["state"].get("status", "unknown")
                                status_icon = "🔵" if status == "dormant" else "🟢"
                                st.markdown(f"{status_icon} {threat.get('name', 'Unknown')} - {status.title()}")
                else:
                    st.info("Threat intelligence will appear here during gameplay")

            st.markdown("---")

            # Phase 5B: Business Impact Dashboard
            st.markdown("### 💰 Business Impact")
            with st.expander("View Financial Impact", expanded=True):
                business_impact = game_state.get("business_impact")

                if business_impact:
                    total_cost = business_impact.get("total_cost", 0)

                    # Total cost banner
                    if total_cost > 0:
                        cost_color = "🔴" if total_cost > 10000000 else "🟠" if total_cost > 1000000 else "🟡"
                        st.markdown(f"### {cost_color} ${total_cost:,.0f}")
                        st.caption("Total estimated cost")
                    else:
                        st.markdown("### 🟢 $0")
                        st.caption("No significant impact yet")

                    st.markdown("---")

                    # Impact breakdown
                    downtime_cost = business_impact.get("downtime_cost", 0)
                    data_loss_cost = business_impact.get("data_loss_cost", 0)
                    compliance_total = sum(business_impact.get("compliance_penalties", {}).values())
                    reputation_cost = business_impact.get("reputation_damage", 0)

                    # Show breakdown only if there's cost
                    if total_cost > 0:
                        st.markdown("**Cost Breakdown:**")

                        if downtime_cost > 0:
                            downtime_hours = business_impact.get("downtime_hours", 0)
                            st.markdown(f"⏱️ **Downtime:** ${downtime_cost:,.0f}")
                            st.caption(f"{downtime_hours:.1f} hours of system downtime")

                        if data_loss_cost > 0:
                            records = business_impact.get("records_compromised", 0)
                            st.markdown(f"🔓 **Data Loss:** ${data_loss_cost:,.0f}")
                            st.caption(f"{records:,} records compromised")

                        if compliance_total > 0:
                            st.markdown(f"⚖️ **Compliance:** ${compliance_total:,.0f}")
                            penalties = business_impact.get("compliance_penalties", {})
                            for framework, amount in penalties.items():
                                st.caption(f"  • {framework}: ${amount:,.0f}")

                        if reputation_cost > 0:
                            st.markdown(f"📉 **Reputation:** ${reputation_cost:,.0f}")
                            st.caption("Brand and customer trust damage")

                        st.markdown("---")

                        # Impact summary
                        description = business_impact.get("impact_description", "")
                        if description:
                            st.info(description)

                        # Recent impact events
                        impact_events = game_state.get("impact_events", [])
                        if impact_events:
                            with st.expander(f"Recent Events ({len(impact_events)})", expanded=False):
                                for event in reversed(impact_events[-5:]):  # Last 5 events
                                    event_type = event.get("event_type", "unknown")
                                    cost = event.get("cost", 0)
                                    severity = event.get("severity", "medium")

                                    # Event icon
                                    icon_map = {
                                        "downtime": "⏱️",
                                        "data_loss": "🔓",
                                        "compliance": "⚖️",
                                        "reputation": "📉"
                                    }
                                    icon = icon_map.get(event_type, "💰")

                                    # Severity color
                                    sev_color = {
                                        "critical": "🔴",
                                        "high": "🟠",
                                        "medium": "🟡",
                                        "low": "🟢"
                                    }.get(severity, "⚪")

                                    st.markdown(f"{icon} {sev_color} ${cost:,.0f}")
                                    desc = event.get("description", "Impact event")
                                    st.caption(desc[:100] + "..." if len(desc) > 100 else desc)
                else:
                    st.info("Business impact tracking will appear here during gameplay")

            st.markdown("---")

            # Phase 5B: Timer & Escalation Dashboard
            st.markdown("### ⏰ Time Pressure")
            with st.expander("View Timers & Escalations", expanded=True):
                timers = game_state.get("timers", [])
                escalation_rules = game_state.get("escalation_rules", [])

                if timers or escalation_rules:
                    # Active Timers
                    if timers:
                        active_timers = [t for t in timers if t.get("remaining_seconds", 0) > 0]
                        expired_timers = [t for t in timers if t.get("remaining_seconds", 0) == 0]

                        if active_timers:
                            st.markdown("**⏱️ Active Timers:**")
                            for timer in sorted(active_timers, key=lambda t: t.get("remaining_seconds", 0)):
                                remaining = timer.get("remaining_seconds", 0)
                                duration = timer.get("duration_seconds", 1)
                                name = timer.get("name", "Timer")
                                is_critical = timer.get("is_critical", False)

                                # Calculate minutes and seconds
                                mins = remaining // 60
                                secs = remaining % 60
                                time_str = f"{mins}:{secs:02d}"

                                # Determine urgency
                                if remaining < 300:  # < 5 minutes
                                    urgency_color = "🔴"
                                    urgency_label = "URGENT"
                                elif remaining < 600:  # < 10 minutes
                                    urgency_color = "🟡"
                                    urgency_label = "Warning"
                                else:
                                    urgency_color = "🟢"
                                    urgency_label = "Active"

                                # Critical badge
                                critical_badge = "🔥 " if is_critical else ""

                                st.markdown(f"{urgency_color} {critical_badge}**{name}**: {time_str}")
                                st.caption(f"{urgency_label} | {timer.get('description', 'Countdown timer')}")

                                # Progress bar
                                percentage = (remaining / duration) * 100 if duration > 0 else 0
                                st.progress(percentage / 100)

                            st.markdown("---")

                        if expired_timers:
                            with st.expander(f"⏱️ Expired Timers ({len(expired_timers)})", expanded=False):
                                for timer in expired_timers:
                                    st.markdown(f"❌ ~~{timer.get('name', 'Timer')}~~ - Expired")
                                    st.caption(timer.get("on_expiry_event", "Time limit exceeded"))

                    # Escalation Rules
                    if escalation_rules:
                        active_rules = [r for r in escalation_rules if not r.get("triggered", False)]
                        triggered_rules = [r for r in escalation_rules if r.get("triggered", False)]

                        if active_rules:
                            st.markdown("**⚠️ Scheduled Escalations:**")

                            # Find next escalation
                            time_elapsed = game_state.get("time_elapsed", 0)
                            next_rules = sorted(active_rules, key=lambda r: r.get("trigger_time_minutes", 999))[:3]

                            for rule in next_rules:
                                trigger_time = rule.get("trigger_time_minutes", 0)
                                minutes_until = max(0, trigger_time - time_elapsed)
                                action = rule.get("action", "unknown")
                                description = rule.get("description", "Escalation event")

                                # Action icon
                                action_icons = {
                                    "threat_escalate": "📈",
                                    "system_degrade": "📉",
                                    "spread": "🔄",
                                    "alert": "🚨"
                                }
                                icon = action_icons.get(action, "⚠️")

                                if minutes_until == 0:
                                    st.markdown(f"{icon} **NOW** - {description}")
                                elif minutes_until < 5:
                                    st.markdown(f"{icon} **{minutes_until}m** - {description} 🔴")
                                else:
                                    st.markdown(f"{icon} T+{trigger_time}m - {description}")
                                    st.caption(f"In {minutes_until} minutes")

                            st.markdown("---")

                        # Show triggered rules count
                        if triggered_rules:
                            st.caption(f"✅ {len(triggered_rules)} escalation(s) already triggered")
                else:
                    st.info("Timers and escalations will appear here during gameplay")

            st.markdown("---")

            # Phase 5B: Resource Management Dashboard
            st.markdown("### 💰 Resource Management")
            with st.expander("View Resources & Action Costs", expanded=True):
                resource_pool = game_state.get("resource_pool")

                if resource_pool:
                    # Action Points
                    st.markdown("**⚡ Action Points**")
                    current_ap = resource_pool.get("action_points", 0)
                    max_ap = resource_pool.get("max_action_points", 10)
                    regen_rate = resource_pool.get("points_per_minute", 0.5)
                    ap_percentage = (current_ap / max_ap * 100) if max_ap > 0 else 0

                    # Color coding based on percentage
                    if ap_percentage > 75:
                        ap_color = "🟢"
                        ap_status = "Good"
                    elif ap_percentage > 25:
                        ap_color = "🟡"
                        ap_status = "Low"
                    else:
                        ap_color = "🔴"
                        ap_status = "Critical"

                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.progress(ap_percentage / 100)
                    with col2:
                        st.metric("Current", f"{current_ap}/{max_ap}")
                    with col3:
                        st.caption(f"{ap_color} {ap_status}")

                    st.caption(f"⚡ Regeneration: {regen_rate} pts/min")
                    st.markdown("---")

                    # Budget
                    st.markdown("**💵 Budget**")
                    budget_remaining = resource_pool.get("budget_remaining", 0)
                    budget_total = resource_pool.get("budget_total", 100000)
                    budget_spent = budget_total - budget_remaining
                    budget_percentage = (budget_remaining / budget_total * 100) if budget_total > 0 else 0

                    # Color coding based on percentage
                    if budget_percentage > 75:
                        budget_color = "🟢"
                        budget_status = "Good"
                    elif budget_percentage > 25:
                        budget_color = "🟡"
                        budget_status = "Low"
                    else:
                        budget_color = "🔴"
                        budget_status = "Critical"

                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.progress(budget_percentage / 100)
                    with col2:
                        st.metric("Remaining", f"${budget_remaining:,.0f}")
                    with col3:
                        st.caption(f"{budget_color} {budget_status}")

                    st.caption(f"💸 Spent: ${budget_spent:,.0f} / ${budget_total:,.0f}")
                    st.markdown("---")

                    # Staff
                    st.markdown("**👥 Staff Availability**")
                    staff_available = resource_pool.get("staff_available", 0)

                    # Staff status
                    if staff_available >= 5:
                        staff_color = "🟢"
                        staff_status = "Good"
                    elif staff_available >= 2:
                        staff_color = "🟡"
                        staff_status = "Moderate"
                    else:
                        staff_color = "🔴"
                        staff_status = "Limited"

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.metric("Available Staff", f"{staff_available}")
                    with col2:
                        st.caption(f"{staff_color} {staff_status}")

                    # Cooldowns
                    tools_on_cooldown = resource_pool.get("tools_on_cooldown", {})

                    if tools_on_cooldown:
                        st.markdown("---")
                        st.markdown("**🔧 Tools on Cooldown**")

                        # Convert cooldown timestamps to remaining time
                        from datetime import datetime
                        now = datetime.utcnow()

                        for tool_name, cooldown_until_str in tools_on_cooldown.items():
                            try:
                                # Parse ISO format timestamp
                                cooldown_until = datetime.fromisoformat(cooldown_until_str.replace('Z', '+00:00'))
                                remaining = (cooldown_until - now).total_seconds()

                                if remaining > 0:
                                    minutes = int(remaining // 60)
                                    seconds = int(remaining % 60)
                                    st.markdown(f"🔧 **{tool_name.title()}**: {minutes}m {seconds}s remaining")
                            except:
                                st.markdown(f"🔧 **{tool_name.title()}**: On cooldown")

                    # Action Cost Reference
                    st.markdown("---")
                    st.markdown("**📋 Action Cost Reference**")

                    action_costs = {
                        "Investigation": [
                            ("Investigate/Analyze", "1 AP", "$0", "1 staff"),
                            ("Check Logs/Monitor", "1 AP", "$0", "1 staff"),
                        ],
                        "Detection": [
                            ("Scan Systems", "2 AP", "$500", "1 staff + 5min cooldown"),
                        ],
                        "Containment": [
                            ("Block/Isolate", "2-3 AP", "$0-1K", "1-2 staff + 5-10min cooldown"),
                            ("Quarantine", "3 AP", "$1K", "2 staff + 10min cooldown"),
                        ],
                        "Mitigation": [
                            ("Patch Vulnerability", "4 AP", "$5K", "3 staff + 30min cooldown"),
                            ("Restore Systems", "5 AP", "$10K", "3 staff + 60min cooldown"),
                            ("Rebuild Systems", "6 AP", "$25K", "4 staff + 60min cooldown"),
                        ],
                        "External Help": [
                            ("Call Vendor", "2 AP", "$50K", "1 staff"),
                            ("Hire Consultant", "2 AP", "$75K", "No staff required"),
                        ],
                        "Communication": [
                            ("Notify/Report/Escalate", "1 AP", "$0", "1 staff"),
                        ],
                    }

                    for category, actions in action_costs.items():
                        with st.expander(f"{category}", expanded=False):
                            for action_name, points, budget, staff in actions:
                                st.markdown(f"**{action_name}**")
                                st.caption(f"Cost: {points}, {budget}, {staff}")

                else:
                    st.info("💰 Resource tracking will be available once the game starts")

            st.markdown("---")

            # Objectives
            st.markdown("### 🎯 Objectives")
            with st.expander("View Objectives", expanded=True):
                objectives = game_state.get("objectives", [])
                if objectives:
                    # Group by status
                    pending = [obj for obj in objectives if obj.get("status", "pending") == "pending"]
                    in_progress = [obj for obj in objectives if obj.get("status") == "in-progress"]
                    completed = [obj for obj in objectives if obj.get("status") == "completed"]
                    failed = [obj for obj in objectives if obj.get("status") == "failed"]

                    # Display in progress first
                    if in_progress:
                        st.markdown("**🔄 In Progress**")
                        for obj in in_progress:
                            obj_type = obj.get("type", "task")
                            difficulty = obj.get("difficulty", "medium")
                            points = obj.get("points", 25)

                            # Emoji based on type
                            type_emoji = {
                                "detect": "🔍", "contain": "🛡️", "mitigate": "🔧",
                                "investigate": "🔬", "protect": "🔐", "report": "📝"
                            }.get(obj_type, "📌")

                            # Color badge for difficulty
                            difficulty_color = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "⚪")

                            st.markdown(f"{type_emoji} **{obj.get('description', 'Objective')}**")
                            st.caption(f"{difficulty_color} {difficulty.title()} | {points} points | {obj.get('success_criteria', 'Complete objective')}")

                            # Time limit warning
                            if obj.get("time_limit_minutes"):
                                st.warning(f"⏱️ Time limit: {obj['time_limit_minutes']} minutes")
                        st.markdown("---")

                    # Then pending
                    if pending:
                        st.markdown("**⏳ Pending**")
                        for obj in pending:
                            obj_type = obj.get("type", "task")
                            points = obj.get("points", 25)
                            type_emoji = {
                                "detect": "🔍", "contain": "🛡️", "mitigate": "🔧",
                                "investigate": "🔬", "protect": "🔐", "report": "📝"
                            }.get(obj_type, "📌")

                            st.markdown(f"{type_emoji} {obj.get('description', 'Objective')} ({points} pts)")
                        st.markdown("---")

                    # Then completed
                    if completed:
                        st.markdown("**✅ Completed**")
                        for obj in completed:
                            st.markdown(f"✅ ~~{obj.get('description', 'Objective')}~~ (+{obj.get('points', 25)} pts)")
                        st.markdown("---")

                    # Finally failed
                    if failed:
                        st.markdown("**❌ Failed**")
                        for obj in failed:
                            st.markdown(f"❌ ~~{obj.get('description', 'Objective')}~~")
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
        response = requests.get(f"{API_BASE_URL}/game/sessions", timeout=DEFAULT_TIMEOUT)
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
                                    timeout=DEFAULT_TIMEOUT
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

                                    # Load scenario - always set it from game_data
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
