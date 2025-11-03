"""
Streamlit Scenario Editor Page - Customize generated scenarios before use.
"""
import streamlit as st
import json
import copy
from datetime import datetime

st.set_page_config(
    page_title="Scenario Editor",
    page_icon="✏️",
    layout="wide"
)

st.title("✏️ Scenario Editor")
st.markdown("Customize your scenario before starting the war game")
st.markdown("---")

# Initialize session state for editing
if "editing_scenario" not in st.session_state:
    st.session_state.editing_scenario = None
if "original_scenario" not in st.session_state:
    st.session_state.original_scenario = None

# Check if there's a scenario to edit
if not st.session_state.get("generated_organization"):
    st.warning("⚠️ No scenario available to edit. Please generate a scenario first.")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📋 Go to Scenario Builder", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Scenario_Builder.py")
else:
    # Initialize editing scenario if not already done
    if st.session_state.editing_scenario is None:
        st.session_state.editing_scenario = copy.deepcopy(st.session_state.generated_organization)
        st.session_state.original_scenario = copy.deepcopy(st.session_state.generated_organization)

    scenario = st.session_state.editing_scenario

    # Show what's being edited
    st.info(f"📝 Editing: **{scenario.get('name', 'Unnamed Organization')}**")

    # Tabs for different editing sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏢 Organization",
        "🏬 Departments",
        "💻 Systems",
        "🔓 Vulnerabilities",
        "👤 Threat Actors",
        "🎯 Game Objectives"
    ])

    # ===== TAB 1: Organization Details =====
    with tab1:
        st.markdown("### Organization Profile")

        col1, col2 = st.columns(2)

        with col1:
            new_name = st.text_input(
                "Organization Name",
                value=scenario.get("name", ""),
                key="edit_org_name"
            )

            new_industry = st.selectbox(
                "Industry",
                ["Financial Services", "Healthcare", "Technology", "Manufacturing",
                 "Retail", "Government", "Education", "Energy/Utilities"],
                index=["Financial Services", "Healthcare", "Technology", "Manufacturing",
                       "Retail", "Government", "Education", "Energy/Utilities"].index(scenario.get("industry", "Technology"))
            )

            new_size = st.selectbox(
                "Size",
                ["small", "medium", "large", "enterprise"],
                index=["small", "medium", "large", "enterprise"].index(scenario.get("size", "medium"))
            )

        with col2:
            new_security_posture = st.selectbox(
                "Security Posture",
                ["weak", "developing", "mature", "advanced"],
                index=["weak", "developing", "mature", "advanced"].index(scenario.get("security_posture", "developing"))
            )

            new_description = st.text_area(
                "Description",
                value=scenario.get("description", ""),
                height=150,
                key="edit_org_desc"
            )

        if st.button("💾 Save Organization Changes", type="primary"):
            scenario["name"] = new_name
            scenario["industry"] = new_industry
            scenario["size"] = new_size
            scenario["security_posture"] = new_security_posture
            scenario["description"] = new_description
            st.success("✅ Organization details updated!")
            st.rerun()

    # ===== TAB 2: Departments =====
    with tab2:
        st.markdown("### Departments")

        departments = scenario.get("departments", [])

        # Display existing departments
        for idx, dept in enumerate(departments):
            with st.expander(f"📂 {dept.get('name', 'Unnamed Department')}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    dept_name = st.text_input(
                        "Department Name",
                        value=dept.get("name", ""),
                        key=f"dept_name_{idx}"
                    )

                    dept_desc = st.text_area(
                        "Description",
                        value=dept.get("description", ""),
                        key=f"dept_desc_{idx}",
                        height=80
                    )

                    dept_function = st.text_input(
                        "Business Function",
                        value=dept.get("business_function", ""),
                        key=f"dept_func_{idx}"
                    )

                    dept_classification = st.selectbox(
                        "Data Classification",
                        ["public", "internal", "confidential", "restricted"],
                        index=["public", "internal", "confidential", "restricted"].index(
                            dept.get("data_classification", "internal")
                        ),
                        key=f"dept_class_{idx}"
                    )

                with col2:
                    st.markdown("**Actions:**")
                    if st.button("💾 Save", key=f"save_dept_{idx}", use_container_width=True):
                        departments[idx]["name"] = dept_name
                        departments[idx]["description"] = dept_desc
                        departments[idx]["business_function"] = dept_function
                        departments[idx]["data_classification"] = dept_classification
                        st.success(f"✅ Saved {dept_name}")
                        st.rerun()

                    if st.button("🗑️ Delete", key=f"del_dept_{idx}", use_container_width=True):
                        departments.pop(idx)
                        st.success(f"✅ Deleted department")
                        st.rerun()

        # Add new department
        st.markdown("---")
        st.markdown("### ➕ Add New Department")
        with st.form("add_department"):
            new_dept_name = st.text_input("Department Name")
            new_dept_desc = st.text_area("Description")
            new_dept_func = st.text_input("Business Function")
            new_dept_class = st.selectbox(
                "Data Classification",
                ["public", "internal", "confidential", "restricted"]
            )

            if st.form_submit_button("Add Department"):
                new_dept = {
                    "id": f"dept_{len(departments) + 1}",
                    "name": new_dept_name,
                    "description": new_dept_desc,
                    "business_function": new_dept_func,
                    "data_classification": new_dept_class,
                    "systems": []
                }
                departments.append(new_dept)
                st.success(f"✅ Added {new_dept_name}")
                st.rerun()

    # ===== TAB 3: Systems =====
    with tab3:
        st.markdown("### IT Systems")

        systems = scenario.get("systems", [])

        # Display existing systems
        for idx, sys in enumerate(systems):
            with st.expander(f"💻 {sys.get('name', 'Unnamed System')}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    sys_name = st.text_input(
                        "System Name",
                        value=sys.get("name", ""),
                        key=f"sys_name_{idx}"
                    )

                    sys_type = st.selectbox(
                        "Type",
                        ["server", "workstation", "database", "web-application", "cloud-service", "network-device"],
                        index=["server", "workstation", "database", "web-application", "cloud-service", "network-device"].index(
                            sys.get("type", "server")
                        ) if sys.get("type") in ["server", "workstation", "database", "web-application", "cloud-service", "network-device"] else 0,
                        key=f"sys_type_{idx}"
                    )

                    sys_os = st.text_input(
                        "Operating System",
                        value=sys.get("operating_system", ""),
                        key=f"sys_os_{idx}"
                    )

                    sys_crit = st.selectbox(
                        "Criticality",
                        ["low", "medium", "high", "critical"],
                        index=["low", "medium", "high", "critical"].index(sys.get("criticality", "medium")),
                        key=f"sys_crit_{idx}"
                    )

                with col2:
                    st.markdown("**Actions:**")
                    if st.button("💾 Save", key=f"save_sys_{idx}", use_container_width=True):
                        systems[idx]["name"] = sys_name
                        systems[idx]["type"] = sys_type
                        systems[idx]["operating_system"] = sys_os
                        systems[idx]["criticality"] = sys_crit
                        st.success(f"✅ Saved {sys_name}")
                        st.rerun()

                    if st.button("🗑️ Delete", key=f"del_sys_{idx}", use_container_width=True):
                        systems.pop(idx)
                        st.success(f"✅ Deleted system")
                        st.rerun()

        # Add new system
        st.markdown("---")
        st.markdown("### ➕ Add New System")
        with st.form("add_system"):
            col1, col2 = st.columns(2)
            with col1:
                new_sys_name = st.text_input("System Name")
                new_sys_type = st.selectbox(
                    "Type",
                    ["server", "workstation", "database", "web-application", "cloud-service", "network-device"]
                )
            with col2:
                new_sys_os = st.text_input("Operating System")
                new_sys_crit = st.selectbox(
                    "Criticality",
                    ["low", "medium", "high", "critical"]
                )

            if st.form_submit_button("Add System"):
                new_sys = {
                    "id": f"sys_{len(systems) + 1}",
                    "name": new_sys_name,
                    "type": new_sys_type,
                    "operating_system": new_sys_os,
                    "criticality": new_sys_crit,
                    "vulnerabilities": []
                }
                systems.append(new_sys)
                st.success(f"✅ Added {new_sys_name}")
                st.rerun()

    # ===== TAB 4: Vulnerabilities =====
    with tab4:
        st.markdown("### Vulnerabilities")

        vulnerabilities = scenario.get("vulnerabilities", [])

        # Display existing vulnerabilities
        for idx, vuln in enumerate(vulnerabilities):
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            with st.expander(
                f"{severity_emoji.get(vuln.get('severity'), '⚪')} {vuln.get('name', 'Unnamed Vulnerability')}",
                expanded=False
            ):
                col1, col2 = st.columns([3, 1])

                with col1:
                    vuln_name = st.text_input(
                        "Vulnerability Name",
                        value=vuln.get("name", ""),
                        key=f"vuln_name_{idx}"
                    )

                    vuln_desc = st.text_area(
                        "Description",
                        value=vuln.get("description", ""),
                        key=f"vuln_desc_{idx}",
                        height=80
                    )

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        vuln_severity = st.selectbox(
                            "Severity",
                            ["low", "medium", "high", "critical"],
                            index=["low", "medium", "high", "critical"].index(vuln.get("severity", "medium")),
                            key=f"vuln_sev_{idx}"
                        )
                    with col_b:
                        vuln_cve = st.text_input(
                            "CVE ID (optional)",
                            value=vuln.get("cve_id", ""),
                            key=f"vuln_cve_{idx}"
                        )
                    with col_c:
                        vuln_exploitable = st.checkbox(
                            "Exploitable",
                            value=vuln.get("exploitable", True),
                            key=f"vuln_exp_{idx}"
                        )

                with col2:
                    st.markdown("**Actions:**")
                    if st.button("💾 Save", key=f"save_vuln_{idx}", use_container_width=True):
                        vulnerabilities[idx]["name"] = vuln_name
                        vulnerabilities[idx]["description"] = vuln_desc
                        vulnerabilities[idx]["severity"] = vuln_severity
                        vulnerabilities[idx]["cve_id"] = vuln_cve if vuln_cve else None
                        vulnerabilities[idx]["exploitable"] = vuln_exploitable
                        st.success(f"✅ Saved vulnerability")
                        st.rerun()

                    if st.button("🗑️ Delete", key=f"del_vuln_{idx}", use_container_width=True):
                        vulnerabilities.pop(idx)
                        st.success(f"✅ Deleted vulnerability")
                        st.rerun()

        # Add new vulnerability
        st.markdown("---")
        st.markdown("### ➕ Add New Vulnerability")
        with st.form("add_vulnerability"):
            new_vuln_name = st.text_input("Vulnerability Name")
            new_vuln_desc = st.text_area("Description")
            col1, col2, col3 = st.columns(3)
            with col1:
                new_vuln_sev = st.selectbox("Severity", ["low", "medium", "high", "critical"])
            with col2:
                new_vuln_cve = st.text_input("CVE ID (optional)")
            with col3:
                new_vuln_exp = st.checkbox("Exploitable", value=True)

            if st.form_submit_button("Add Vulnerability"):
                new_vuln = {
                    "id": f"vuln_{len(vulnerabilities) + 1}",
                    "name": new_vuln_name,
                    "description": new_vuln_desc,
                    "severity": new_vuln_sev,
                    "cve_id": new_vuln_cve if new_vuln_cve else None,
                    "exploitable": new_vuln_exp,
                    "affected_systems": []
                }
                vulnerabilities.append(new_vuln)
                st.success(f"✅ Added vulnerability")
                st.rerun()

    # ===== TAB 5: Threat Actors =====
    with tab5:
        st.markdown("### Threat Actors")

        threat_actors = scenario.get("threat_actors", [])

        # Display existing threat actors
        for idx, actor in enumerate(threat_actors):
            with st.expander(f"👤 {actor.get('name', 'Unnamed Threat Actor')}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    actor_name = st.text_input(
                        "Threat Actor Name",
                        value=actor.get("name", ""),
                        key=f"actor_name_{idx}"
                    )

                    actor_desc = st.text_area(
                        "Description",
                        value=actor.get("description", ""),
                        key=f"actor_desc_{idx}",
                        height=80
                    )

                    col_a, col_b = st.columns(2)
                    with col_a:
                        actor_motivation = st.selectbox(
                            "Motivation",
                            ["financial", "espionage", "hacktivism", "nation-state", "insider"],
                            index=["financial", "espionage", "hacktivism", "nation-state", "insider"].index(
                                actor.get("motivation", "financial")
                            ) if actor.get("motivation") in ["financial", "espionage", "hacktivism", "nation-state", "insider"] else 0,
                            key=f"actor_mot_{idx}"
                        )
                    with col_b:
                        actor_soph = st.selectbox(
                            "Sophistication",
                            ["low", "medium-low", "medium", "medium-high", "high", "nation-state"],
                            index=["low", "medium-low", "medium", "medium-high", "high", "nation-state"].index(
                                actor.get("sophistication", "medium")
                            ) if actor.get("sophistication") in ["low", "medium-low", "medium", "medium-high", "high", "nation-state"] else 2,
                            key=f"actor_soph_{idx}"
                        )

                    # TTPs editing
                    st.markdown("**TTPs (Tactics, Techniques, Procedures):**")
                    ttps_text = st.text_area(
                        "One per line",
                        value="\n".join(actor.get("ttps", [])),
                        key=f"actor_ttps_{idx}",
                        height=100
                    )

                with col2:
                    st.markdown("**Actions:**")
                    if st.button("💾 Save", key=f"save_actor_{idx}", use_container_width=True):
                        threat_actors[idx]["name"] = actor_name
                        threat_actors[idx]["description"] = actor_desc
                        threat_actors[idx]["motivation"] = actor_motivation
                        threat_actors[idx]["sophistication"] = actor_soph
                        threat_actors[idx]["ttps"] = [ttp.strip() for ttp in ttps_text.split("\n") if ttp.strip()]
                        st.success(f"✅ Saved {actor_name}")
                        st.rerun()

                    if st.button("🗑️ Delete", key=f"del_actor_{idx}", use_container_width=True):
                        threat_actors.pop(idx)
                        st.success(f"✅ Deleted threat actor")
                        st.rerun()

        # Add new threat actor
        st.markdown("---")
        st.markdown("### ➕ Add New Threat Actor")
        with st.form("add_threat_actor"):
            new_actor_name = st.text_input("Threat Actor Name")
            new_actor_desc = st.text_area("Description")
            col1, col2 = st.columns(2)
            with col1:
                new_actor_mot = st.selectbox(
                    "Motivation",
                    ["financial", "espionage", "hacktivism", "nation-state", "insider"]
                )
            with col2:
                new_actor_soph = st.selectbox(
                    "Sophistication",
                    ["low", "medium-low", "medium", "medium-high", "high", "nation-state"]
                )
            new_actor_ttps = st.text_area("TTPs (one per line)")

            if st.form_submit_button("Add Threat Actor"):
                new_actor = {
                    "id": f"threat_{len(threat_actors) + 1}",
                    "name": new_actor_name,
                    "description": new_actor_desc,
                    "motivation": new_actor_mot,
                    "sophistication": new_actor_soph,
                    "ttps": [ttp.strip() for ttp in new_actor_ttps.split("\n") if ttp.strip()],
                    "targets": []
                }
                threat_actors.append(new_actor)
                st.success(f"✅ Added {new_actor_name}")
                st.rerun()

    # ===== TAB 6: Game Objectives =====
    with tab6:
        st.markdown("### Game Objectives")
        st.info("Define custom objectives for players to complete during the war game.")

        # Initialize objectives if not present
        if "objectives" not in scenario:
            scenario["objectives"] = []

        objectives = scenario["objectives"]

        # Display existing objectives
        for idx, obj in enumerate(objectives):
            col1, col2 = st.columns([4, 1])
            with col1:
                obj_text = st.text_input(
                    f"Objective {idx + 1}",
                    value=obj if isinstance(obj, str) else obj.get("description", ""),
                    key=f"obj_{idx}"
                )
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_obj_{idx}"):
                    objectives.pop(idx)
                    st.rerun()

            # Update objective text
            if isinstance(obj, str):
                objectives[idx] = obj_text
            else:
                objectives[idx]["description"] = obj_text

        # Add new objective
        st.markdown("---")
        with st.form("add_objective"):
            new_obj = st.text_input("New Objective")
            if st.form_submit_button("➕ Add Objective"):
                objectives.append(new_obj)
                st.success("✅ Added objective")
                st.rerun()

        # Suggested objectives
        st.markdown("---")
        st.markdown("### 💡 Suggested Objectives")
        suggestions = [
            "Identify the initial infection vector",
            "Contain the threat within 30 minutes",
            "Preserve critical business systems",
            "Collect forensic evidence",
            "Notify relevant stakeholders",
            "Implement remediation measures",
            "Prevent data exfiltration",
            "Restore normal operations"
        ]

        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(f"➕ {suggestion}", key=f"sugg_{i}", use_container_width=True):
                    if suggestion not in objectives:
                        objectives.append(suggestion)
                        st.success(f"✅ Added: {suggestion}")
                        st.rerun()

    # ===== Action Buttons =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("↩️ Revert All Changes", use_container_width=True):
            st.session_state.editing_scenario = copy.deepcopy(st.session_state.original_scenario)
            st.success("✅ Reverted to original scenario")
            st.rerun()

    with col2:
        if st.button("💾 Save & Continue", use_container_width=True, type="primary"):
            # Save the edited scenario back
            st.session_state.generated_organization = copy.deepcopy(st.session_state.editing_scenario)
            st.success("✅ Scenario saved!")
            st.info("You can now start the war game with your customized scenario.")

    with col3:
        if st.button("🎮 Save & Start War Game", use_container_width=True, type="primary"):
            # Save and switch to war game
            st.session_state.generated_organization = copy.deepcopy(st.session_state.editing_scenario)
            st.session_state.active_scenario = copy.deepcopy(st.session_state.editing_scenario)
            st.switch_page("pages/2_War_Game.py")

    with col4:
        if st.button("❌ Cancel", use_container_width=True):
            st.switch_page("pages/1_Scenario_Builder.py")

# Sidebar
with st.sidebar:
    st.markdown("## Navigation")

    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")

    if st.button("📋 Scenario Builder", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")

    st.markdown("---")

    st.markdown("## Editing Tips")
    st.markdown("""
    - **Organization**: Basic profile info
    - **Departments**: Business units
    - **Systems**: IT infrastructure
    - **Vulnerabilities**: Security weaknesses
    - **Threat Actors**: Adversaries
    - **Objectives**: Game goals

    Changes are saved per-tab. Use the
    bottom buttons to finalize or revert.
    """)
