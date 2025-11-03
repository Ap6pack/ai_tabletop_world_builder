"""
Streamlit Scenario Builder Page - Generate cybersecurity training scenarios.
"""
import streamlit as st
import json
import requests
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import PLAYER_ROLES, ORG_SIZES, COMPLEXITY_LEVELS, SCENARIO_TYPES, DIFFICULTY_LEVELS

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Scenario Builder",
    page_icon="",
    layout="wide"
)

st.title("Scenario Builder")
st.markdown("Generate custom cybersecurity training scenarios")
st.markdown("---")

# Initialize session state
if "generated_organization" not in st.session_state:
    st.session_state.generated_organization = None

# Scenario configuration
st.markdown("### Scenario Configuration")

col1, col2 = st.columns(2)

with col1:
    industry = st.selectbox(
        "Industry Sector",
        [
            "Financial Services",
            "Healthcare",
            "Technology",
            "Retail",
            "Manufacturing",
            "Government",
            "Education",
            "Energy/Utilities"
        ]
    )

    organization_size = st.selectbox(
        "Organization Size",
        ["Small (< 100 employees)", "Medium (100-1000)", "Large (1000-5000)", "Enterprise (5000+)"]
    )

    complexity = st.select_slider(
        "Scenario Complexity",
        options=["Basic", "Moderate", "Complex"],
        value="Moderate"
    )

with col2:
    scenario_type = st.selectbox(
        "Scenario Type",
        [
            "Incident Response",
            "Threat Hunting",
            "Vulnerability Management",
            "Compliance Audit"
        ]
    )

    difficulty = st.selectbox(
        "Difficulty Level",
        ["Beginner", "Intermediate", "Advanced", "Expert"]
    )

    duration = st.slider(
        "Expected Duration (minutes)",
        min_value=15,
        max_value=240,
        value=60,
        step=15
    )

# Focus areas
st.markdown("### Focus Areas")
focus_areas = st.multiselect(
    "Select specific threat types or security domains to emphasize:",
    [
        "Ransomware",
        "Phishing/Social Engineering",
        "Insider Threats",
        "APT/Nation-State",
        "Data Exfiltration",
        "Malware Analysis",
        "Network Intrusion",
        "Cloud Security",
        "Zero-Day Vulnerabilities",
        "Supply Chain Attacks"
    ]
)

# Player role
st.markdown("### Player Role")
player_role = st.radio(
    "What role will trainees assume?",
    list(PLAYER_ROLES.keys())
)

# Learning objectives
st.markdown("### Learning Objectives")
learning_objectives = st.text_area(
    "Specific skills or knowledge to develop (optional):",
    placeholder="e.g., Practice log analysis, improve threat detection, understand attack chains",
    height=100
)

st.markdown("---")

# Generate button
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button("Generate Scenario", use_container_width=True, type="primary"):
        # Create a progress container
        progress_text = st.empty()
        progress_bar = st.progress(0)

        try:
            progress_text.text("🔧 Preparing scenario generation...")
            progress_bar.progress(10)

            # Prepare API request using constants for proper mapping
            payload = {
                "industry": industry,
                "size": ORG_SIZES.get(organization_size, "medium"),
                "complexity": COMPLEXITY_LEVELS.get(complexity, "moderate"),
                "focus_areas": focus_areas if focus_areas else None,
                "num_departments": 3
            }

            progress_text.text("🏢 Generating organization profile...")
            progress_bar.progress(20)

            # Call API with extended timeout
            response = requests.post(
                f"{API_BASE_URL}/scenarios/generate",
                json=payload,
                timeout=180  # Increased to 3 minutes
            )

            progress_bar.progress(90)

            if response.status_code == 200:
                organization_data = response.json()
                progress_bar.progress(100)
                progress_text.empty()
                progress_bar.empty()

                st.success("✅ Scenario generated successfully!")

                # Store full organization data
                st.session_state.generated_organization = organization_data
                st.session_state.scenario_metadata = {
                    "scenario_type": SCENARIO_TYPES.get(scenario_type, "incident-response"),
                    "difficulty": DIFFICULTY_LEVELS.get(difficulty, "intermediate"),
                    "duration_minutes": duration,
                    "focus_areas": focus_areas,
                    "player_role": PLAYER_ROLES.get(player_role, "soc-analyst")
                }
            else:
                progress_text.empty()
                progress_bar.empty()
                st.error(f"❌ Failed to generate scenario: {response.status_code}")
                st.error(response.text)

        except requests.exceptions.Timeout:
            progress_text.empty()
            progress_bar.empty()
            st.error("⏱️ Request timed out after 3 minutes.")
            st.warning("**Troubleshooting tips:**")
            st.markdown("""
            - The LLM API might be slow or rate-limited
            - Try reducing complexity to 'Basic'
            - Check your API key and quotas
            - Review backend logs for errors
            """)
        except requests.exceptions.ConnectionError:
            progress_text.empty()
            progress_bar.empty()
            st.error("🔌 Could not connect to API. Make sure the backend is running on http://127.0.0.1:8000")
            st.info("Run: `uvicorn api.main:app --reload`")
        except Exception as e:
            progress_text.empty()
            progress_bar.empty()
            st.error(f"❌ Error: {str(e)}")
            st.info("Check the backend logs for more details.")

# Display generated scenario
if st.session_state.generated_organization:
    st.markdown("---")
    st.markdown("### Generated Scenario")

    org = st.session_state.generated_organization
    metadata = st.session_state.get("scenario_metadata", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Organization", org.get("name", "Unknown"))
        st.metric("Industry", org.get("industry", "Unknown"))
    with col2:
        st.metric("Size", org.get("size", "Unknown").capitalize())
        st.metric("Security Posture", org.get("security_posture", "Unknown").capitalize())
    with col3:
        st.metric("Departments", len(org.get("departments", [])))
        st.metric("Systems", len(org.get("systems", [])))

    # Organization details
    with st.expander("Organization Details", expanded=True):
        st.markdown(f"**Organization Profile:**")
        st.markdown(f"- **Name:** {org.get('name', 'N/A')}")
        st.markdown(f"- **Industry:** {org.get('industry', 'N/A')}")
        st.markdown(f"- **Size:** {org.get('size', 'N/A').capitalize()}")
        st.markdown(f"- **Security Posture:** {org.get('security_posture', 'N/A').capitalize()}")
        st.markdown(f"- **Description:** {org.get('description', 'N/A')}")

        st.markdown("\n**Infrastructure:**")
        st.markdown(f"- **Departments:** {len(org.get('departments', []))}")
        st.markdown(f"- **Systems:** {len(org.get('systems', []))}")
        st.markdown(f"- **Vulnerabilities:** {len(org.get('vulnerabilities', []))}")
        st.markdown(f"- **Threat Actors:** {len(org.get('threat_actors', []))}")

        if org.get("compliance_frameworks"):
            st.markdown(f"\n**Compliance Frameworks:** {', '.join(org['compliance_frameworks'])}")

    # Departments
    if org.get("departments"):
        with st.expander("Departments & Systems"):
            for dept in org["departments"]:
                st.markdown(f"### {dept.get('name', 'Unknown Department')}")
                st.markdown(f"*{dept.get('description', '')}")
                st.markdown(f"**Business Function:** {dept.get('business_function', 'N/A')}")
                st.markdown(f"**Data Classification:** {dept.get('data_classification', 'N/A').capitalize()}")

                # Show systems in this department
                dept_systems = [s for s in org.get("systems", []) if any(s['id'] in sys_id for sys_id in dept.get('systems', []))]
                if dept_systems:
                    st.markdown(f"**Systems ({len(dept_systems)}):**")
                    for sys in dept_systems[:3]:  # Show first 3
                        st.markdown(f"  - {sys.get('name', 'Unknown')} ({sys.get('type', 'unknown')})")
                st.markdown("---")

    # Vulnerabilities
    if org.get("vulnerabilities"):
        with st.expander("Vulnerabilities Discovered"):
            vuln_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for vuln in org["vulnerabilities"]:
                vuln_count[vuln.get("severity", "low")] += 1

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔴 Critical", vuln_count["critical"])
            col2.metric("🟠 High", vuln_count["high"])
            col3.metric("🟡 Medium", vuln_count["medium"])
            col4.metric("🟢 Low", vuln_count["low"])

            st.markdown("\n**Top Vulnerabilities:**")
            for vuln in org["vulnerabilities"][:5]:  # Show top 5
                severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                st.markdown(f"{severity_emoji.get(vuln.get('severity'), '⚪')} **{vuln.get('name', 'Unknown')}**")
                st.markdown(f"  - Severity: {vuln.get('severity', 'unknown').upper()}")
                if vuln.get('cve_id'):
                    st.markdown(f"  - CVE: {vuln['cve_id']}")
                st.markdown(f"  - {vuln.get('description', '')[:200]}...")
                st.markdown("")

    # Threat actors
    if org.get("threat_actors"):
        with st.expander("Threat Landscape"):
            for actor in org["threat_actors"]:
                st.markdown(f"### {actor.get('name', 'Unknown Threat Actor')}")
                st.markdown(f"*{actor.get('description', '')}")
                st.markdown(f"**Motivation:** {actor.get('motivation', 'unknown').capitalize()}")
                st.markdown(f"**Sophistication:** {actor.get('sophistication', 'unknown').replace('-', ' ').title()}")

                if actor.get("ttps"):
                    st.markdown(f"**TTPs:**")
                    for ttp in actor["ttps"][:5]:
                        st.markdown(f"  - {ttp}")

                if actor.get("targets"):
                    st.markdown(f"**Targets:** {', '.join(actor['targets'])}")
                st.markdown("---")

    # Action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Scenario is automatically saved by the API
        st.info("✅ Auto-saved")

    with col2:
        if st.button("✏️ Customize Scenario", use_container_width=True):
            st.session_state.active_scenario = org
            st.session_state.scenario_metadata = metadata
            st.switch_page("pages/4_Scenario_Editor.py")

    with col3:
        if st.button("🎮 Start War Game", use_container_width=True, type="primary"):
            st.session_state.active_scenario = org
            st.session_state.scenario_metadata = metadata
            st.switch_page("pages/2_War_Game.py")

    with col4:
        if st.button("🔄 Generate New", use_container_width=True):
            st.session_state.generated_organization = None
            st.session_state.scenario_metadata = None
            st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("## Saved Scenarios")
    st.markdown("Load a previously generated scenario:")

    try:
        # List scenarios from API
        response = requests.get(f"{API_BASE_URL}/scenarios/list", timeout=5)
        if response.status_code == 200:
            scenarios_list = response.json()

            if scenarios_list:
                # Create selection dropdown
                scenario_names = [f"{s['name']} ({s['industry']})" for s in scenarios_list]
                selected_scenario = st.selectbox("Select a scenario:", [""] + scenario_names)

                if selected_scenario:
                    # Find selected scenario
                    selected_index = scenario_names.index(selected_scenario)
                    scenario_info = scenarios_list[selected_index]

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📂 Load", use_container_width=True):
                            try:
                                # Load scenario from API
                                load_response = requests.get(
                                    f"{API_BASE_URL}/scenarios/{scenario_info['filename']}",
                                    timeout=10
                                )
                                if load_response.status_code == 200:
                                    st.session_state.generated_organization = load_response.json()
                                    st.success(f"✅ Loaded {scenario_info['name']}")
                                    st.rerun()
                                else:
                                    st.error("Failed to load scenario")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                    with col2:
                        if st.button("🗑️ Delete", use_container_width=True):
                            try:
                                delete_response = requests.delete(
                                    f"{API_BASE_URL}/scenarios/{scenario_info['filename']}",
                                    timeout=5
                                )
                                if delete_response.status_code == 200:
                                    st.success("✅ Scenario deleted")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete scenario")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                    # Show scenario details
                    with st.expander("Details"):
                        st.markdown(f"**Name:** {scenario_info['name']}")
                        st.markdown(f"**Industry:** {scenario_info['industry']}")
                        st.markdown(f"**Size:** {scenario_info['size']}")
                        st.markdown(f"**Created:** {scenario_info['created_at'][:10]}")
                        st.markdown(f"**File Size:** {scenario_info['file_size'] / 1024:.1f} KB")
            else:
                st.info("No saved scenarios yet. Generate one to get started!")
        else:
            st.warning("Could not load scenarios list")
    except requests.exceptions.ConnectionError:
        st.warning("API not connected")
    except Exception as e:
        st.warning(f"Error loading scenarios: {str(e)}")

    st.markdown("---")
    st.markdown("## Help")
    with st.expander("How to use"):
        st.markdown("""
        1. **Configure** your scenario parameters
        2. **Generate** a custom organization and threat landscape
        3. **Review** the generated scenario details
        4. **Start War Game** to begin training
        5. **Load** previous scenarios from the sidebar
        """)
