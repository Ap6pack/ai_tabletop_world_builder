#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Streamlit Scenario Library Page - Browse, rate, share, and fork scenarios.
"""

import os
import sys

import requests
import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT

st.set_page_config(page_title="Scenario Library", page_icon="", layout="wide")

st.title("Scenario Library")
st.markdown("Browse, rate, and fork community cybersecurity scenarios")
st.markdown("---")

# --- Search and Filters ---
col_search, col_category, col_difficulty = st.columns([3, 1, 1])

with col_search:
    search_query = st.text_input("Search scenarios", placeholder="e.g., ransomware, APT, healthcare...")

with col_category:
    category_filter = st.selectbox(
        "Category",
        ["All", "incident-response", "threat-hunting", "compliance-drill"],
    )

with col_difficulty:
    difficulty_filter = st.selectbox(
        "Difficulty",
        ["All", "beginner", "intermediate", "advanced", "expert"],
    )

# --- Fetch scenarios ---
scenarios = []
try:
    if search_query:
        response = requests.get(
            f"{API_BASE_URL}/library/search",
            params={"q": search_query},
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code == 200:
            scenarios = response.json().get("results", [])
    else:
        params = {"sort_by": "rating"}
        if category_filter != "All":
            params["category"] = category_filter
        if difficulty_filter != "All":
            params["difficulty"] = difficulty_filter
        response = requests.get(
            f"{API_BASE_URL}/library/scenarios",
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code == 200:
            scenarios = response.json().get("scenarios", [])
except requests.exceptions.ConnectionError:
    st.error("Could not connect to API. Ensure the backend is running.")
except Exception as exc:
    st.error(f"Error fetching scenarios: {exc}")

# --- Display scenarios ---
st.markdown(f"### Scenarios ({len(scenarios)})")

if not scenarios:
    st.info("No scenarios found. Try adjusting your filters or add a new scenario.")
else:
    for idx in range(0, len(scenarios), 2):
        cols = st.columns(2)
        for col_idx, col in enumerate(cols):
            s_idx = idx + col_idx
            if s_idx >= len(scenarios):
                break
            scenario = scenarios[s_idx]
            with col, st.container(border=True):
                name = scenario.get("name", "Untitled")
                diff = scenario.get("difficulty", "intermediate")
                db = {
                    "beginner": "🟢 Beginner",
                    "intermediate": "🟡 Intermediate",
                    "advanced": "🟠 Advanced",
                    "expert": "🔴 Expert",
                }
                st.markdown(f"**{name}**  &nbsp; {db.get(diff, diff.title())}")
                rating = scenario.get("rating", 0)
                filled = int(round(rating))
                stars = ("★" * filled) + ("☆" * (5 - filled))
                st.caption(
                    f"{stars} {rating:.1f} ({scenario.get('rating_count', 0)} ratings) "
                    f"| {scenario.get('category', 'N/A')} | {scenario.get('industry', 'N/A')}"
                )
                desc = scenario.get("description", "")
                st.markdown(desc[:200] + ("..." if len(desc) > 200 else ""))
                tags = scenario.get("tags", [])
                if tags:
                    st.caption(" ".join(f"`{t}`" for t in tags[:6]))

                # Actions
                btn_cols = st.columns(3)
                scenario_id = scenario.get("id", "")
                with btn_cols[0]:
                    if st.button(
                        "View",
                        key=f"view_{scenario_id}_{s_idx}",
                        use_container_width=True,
                    ):
                        st.session_state["library_selected"] = scenario_id
                with btn_cols[1]:
                    if st.button(
                        "Fork",
                        key=f"fork_{scenario_id}_{s_idx}",
                        use_container_width=True,
                    ):
                        try:
                            resp = requests.post(
                                f"{API_BASE_URL}/library/scenarios/{scenario_id}/fork",
                                json={"user_id": "local_user"},
                                timeout=DEFAULT_TIMEOUT,
                            )
                            if resp.status_code == 200:
                                st.success("Scenario forked!")
                                st.rerun()
                            else:
                                st.error("Fork failed")
                        except Exception as e:
                            st.error(f"Error: {e}")
                with btn_cols[2]:
                    user_rating = st.selectbox(
                        "Rate",
                        [0, 1, 2, 3, 4, 5],
                        key=f"rate_{scenario_id}_{s_idx}",
                        label_visibility="collapsed",
                    )
                    if user_rating > 0:
                        try:
                            resp = requests.post(
                                f"{API_BASE_URL}/library/scenarios/{scenario_id}/rate",
                                json={"rating": user_rating},
                                timeout=DEFAULT_TIMEOUT,
                            )
                            if resp.status_code == 200:
                                st.caption(f"Rated {user_rating}")
                        except Exception:  # noqa: S110 — best-effort UI rating, failure is non-critical
                            pass

# --- Selected scenario detail view ---
selected_id = st.session_state.get("library_selected")
if selected_id:
    st.markdown("---")
    st.markdown("### Scenario Details")
    try:
        detail_resp = requests.get(
            f"{API_BASE_URL}/library/scenarios/{selected_id}",
            timeout=DEFAULT_TIMEOUT,
        )
        if detail_resp.status_code == 200:
            detail = detail_resp.json()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Industry", detail.get("industry", "N/A"))
                st.metric("Author", detail.get("author", "N/A"))
            with col2:
                st.metric("Difficulty", detail.get("difficulty", "N/A").title())
                st.metric("Category", detail.get("category", "N/A"))
            with col3:
                st.metric("Rating", f"{detail.get('rating', 0):.1f} / 5.0")
                st.metric("Visibility", detail.get("visibility", "N/A").title())

            st.markdown(f"**Description:** {detail.get('description', 'N/A')}")

            tags = detail.get("tags", [])
            if tags:
                st.markdown("**Tags:** " + ", ".join(f"`{t}`" for t in tags))

            if detail.get("original_id"):
                st.caption(f"Forked from: {detail['original_id']}")

            if st.button("Close details"):
                del st.session_state["library_selected"]
                st.rerun()
        else:
            st.warning("Could not load scenario details.")
    except Exception as exc:
        st.error(f"Error loading details: {exc}")

# --- Templates Section ---
st.markdown("---")
st.markdown("### Pre-Built Templates")
st.caption("Curated scenario templates ready for immediate use")

try:
    tpl_resp = requests.get(f"{API_BASE_URL}/library/templates", timeout=DEFAULT_TIMEOUT)
    if tpl_resp.status_code == 200:
        templates = tpl_resp.json().get("templates", [])
        if templates:
            for tidx in range(0, len(templates), 3):
                tpl_cols = st.columns(3)
                for tc_idx, tc in enumerate(tpl_cols):
                    t_idx = tidx + tc_idx
                    if t_idx >= len(templates):
                        break
                    tpl = templates[t_idx]
                    with tc, st.container(border=True):
                        st.markdown(f"**{tpl.get('name', 'Template')}**")
                        diff = tpl.get("difficulty", "intermediate")
                        db = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🟠", "expert": "🔴"}
                        st.caption(f"{db.get(diff, '')} {diff.title()} | {tpl.get('category', 'N/A')}")
                        desc = tpl.get("description", "")
                        st.markdown(desc[:150] + ("..." if len(desc) > 150 else ""))
                        tpl_tags = tpl.get("tags", [])
                        if tpl_tags:
                            st.caption(" ".join(f"`{t}`" for t in tpl_tags[:4]))
        else:
            st.info("No templates available.")
    else:
        st.warning("Could not load templates.")
except requests.exceptions.ConnectionError:
    st.warning("API not connected")
except Exception as exc:
    st.warning(f"Error loading templates: {exc}")

# --- Sidebar ---
with st.sidebar:
    st.markdown("## Navigation")

    if st.button("Home", use_container_width=True):
        st.switch_page("Home.py")

    if st.button("Scenario Builder", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")

    if st.button("War Game", use_container_width=True):
        st.switch_page("pages/2_War_Game.py")

    st.markdown("---")
    st.markdown("## About")
    st.markdown(
        "Discover, share, and fork community cybersecurity scenarios. "
        "Categories: Incident Response, Threat Hunting, Compliance Drill."
    )
