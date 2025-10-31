"""
Streamlit Scenario Builder Page - Generate cybersecurity training scenarios.
"""
import streamlit as st
import json
from datetime import datetime

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
    ["SOC Analyst", "Incident Responder", "Security Engineer", "CISO", "Mixed Team"]
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
        with st.spinner("Generating scenario... This may take a minute."):
            # TODO: Call API to generate scenario
            st.success("Scenario generated successfully!")
            st.session_state.generated_organization = {
                "id": f"org_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "name": f"Example {industry} Corp",
                "industry": industry,
                "size": organization_size.split()[0].lower(),
                "scenario_type": scenario_type,
                "difficulty": difficulty.lower(),
                "duration_minutes": duration,
                "focus_areas": focus_areas,
                "player_role": player_role.lower().replace(" ", "-")
            }

# Display generated scenario
if st.session_state.generated_organization:
    st.markdown("---")
    st.markdown("### Generated Scenario")

    org = st.session_state.generated_organization

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Organization", org["name"])
        st.metric("Industry", org["industry"])
    with col2:
        st.metric("Size", org["size"].capitalize())
        st.metric("Difficulty", org["difficulty"].capitalize())
    with col3:
        st.metric("Duration", f"{org['duration_minutes']} min")
        st.metric("Type", org["scenario_type"])

    # Scenario details (placeholder)
    with st.expander("Organization Details", expanded=True):
        st.markdown("""
        **Organization Profile:**
        - Name: Example Financial Services Corp
        - Industry: Financial Services
        - Size: Medium (500 employees)
        - Security Posture: Developing

        **Infrastructure:**
        - 3 departments: IT Operations, Finance, Customer Service
        - 12 critical systems identified
        - 8 vulnerabilities discovered
        - 2 active threat actors

        *(This is placeholder data - full generation will be implemented)*
        """)

    with st.expander("Scenario Objectives"):
        st.markdown("""
        **Training Objectives:**
        1. Detect and respond to ransomware infection
        2. Practice incident containment procedures
        3. Coordinate cross-team communication
        4. Execute business continuity plans

        **Success Criteria:**
        - Identify initial compromise vector
        - Contain spread within 30 minutes
        - Preserve critical data
        - Maintain stakeholder communication
        """)

    with st.expander("Threat Landscape"):
        st.markdown("""
        **Active Threats:**
        - **Threat Actor**: Conti Ransomware Group
          - Sophistication: Organized Crime
          - Target: Financial data and customer records
          - TTPs: Phishing, lateral movement, data encryption

        **Vulnerabilities:**
        - CVE-2023-XXXX: Unpatched Exchange Server
        - Weak MFA implementation on VPN
        - Insufficient endpoint detection coverage
        """)

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Save Scenario", use_container_width=True):
            # TODO: Save scenario to file
            st.success("Scenario saved to scenarios/generated/")

    with col2:
        if st.button("Start War Game", use_container_width=True, type="primary"):
            st.session_state.active_scenario = org
            st.switch_page("pages/2_War_Game.py")

    with col3:
        if st.button("Generate New", use_container_width=True):
            st.session_state.generated_organization = None
            st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("## Scenario Templates")
    st.markdown("Quick start with pre-configured scenarios:")

    if st.button("Healthcare Ransomware", use_container_width=True):
        st.info("Coming soon")

    if st.button("Banking APT Attack", use_container_width=True):
        st.info("Coming soon")

    if st.button("Manufacturing Supply Chain", use_container_width=True):
        st.info("Coming soon")

    st.markdown("---")
    st.markdown("## Help")
    with st.expander("How to use"):
        st.markdown("""
        1. **Configure** your scenario parameters
        2. **Generate** a custom organization and threat landscape
        3. **Review** the generated scenario details
        4. **Save** for later or **start** immediately
        """)
