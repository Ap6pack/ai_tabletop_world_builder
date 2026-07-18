#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Streamlit After Action Review Page - Post-game analysis and decision evaluation.
"""

import os
import sys

import plotly.graph_objects as go
import requests
import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT, LONG_OPERATION_TIMEOUT

st.set_page_config(page_title="After Action Review", page_icon="📊", layout="wide")

st.title("📊 After Action Review")
st.markdown("Post-game analysis of decisions, performance, and training recommendations")
st.markdown("---")

GRADE_COLORS = {
    "A": "#2ecc71",
    "A+": "#27ae60",
    "A-": "#2ecc71",
    "B": "#3498db",
    "B+": "#2980b9",
    "B-": "#3498db",
    "C": "#f39c12",
    "C+": "#e67e22",
    "C-": "#f39c12",
    "D": "#e74c3c",
    "D+": "#c0392b",
    "D-": "#e74c3c",
    "F": "#8e44ad",
}
IMPACT_LABELS = {"positive": "🟢 Positive", "neutral": "🟡 Neutral", "negative": "🔴 Negative"}
DIFFICULTY_LABELS = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}


def _score_icon(score: int) -> str:
    return "🟢" if score > 70 else ("🟡" if score >= 40 else "🔴")


# --- Session Selector ---
st.markdown("### Select Game Session")

sessions = []
try:
    resp = requests.get(f"{API_BASE_URL}/game/sessions", timeout=DEFAULT_TIMEOUT)
    if resp.status_code == 200:
        all_sessions = resp.json().get("sessions", [])
        sessions = [s for s in all_sessions if s.get("status") != "in-progress"]
except requests.exceptions.RequestException:
    st.error("Could not connect to the API server. Ensure the backend is running.")
except Exception as e:
    st.error(f"Error fetching sessions: {e}")

if not sessions:
    st.info("No completed game sessions found. Complete a war game first to generate an AAR.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎮 Go to War Game", use_container_width=True, type="primary"):
            st.switch_page("pages/2_War_Game.py")
    with col2:
        if st.button("📋 Scenario Builder", use_container_width=True):
            st.switch_page("pages/1_Scenario_Builder.py")
else:
    session_labels = [
        f"{s.get('organization', 'Unknown')[:30]} | {s.get('status', '').title()} | Score: {s.get('score', 0)}"
        for s in sessions
    ]
    selected_idx = st.selectbox(
        "Completed Sessions",
        range(len(session_labels)),
        format_func=lambda i: session_labels[i],
    )
    selected_session = sessions[selected_idx]
    session_id = selected_session["session_id"]

    # --- Generate / View AAR ---
    col_gen, col_view = st.columns(2)
    with col_gen:
        generate_clicked = st.button("Generate AAR", use_container_width=True, type="primary")
    with col_view:
        view_clicked = st.button("View Existing AAR", use_container_width=True)

    aar = None

    if generate_clicked:
        with st.spinner("Generating After Action Review..."):
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/analytics/aar/{session_id}",
                    params={"include_alternatives": True},
                    timeout=LONG_OPERATION_TIMEOUT,
                )
                if resp.status_code == 200:
                    aar = resp.json()
                    st.session_state["aar_data"] = aar
                else:
                    st.error(f"Failed to generate AAR (HTTP {resp.status_code})")
                    try:
                        st.error(f"Details: {resp.json().get('detail', resp.text[:300])}")
                    except Exception:
                        st.error(resp.text[:300])
            except requests.exceptions.RequestException:
                st.error("Network error: could not reach the API server.")
            except Exception as e:
                st.error(f"Error generating AAR: {e}")

    if view_clicked:
        with st.spinner("Fetching After Action Review..."):
            try:
                resp = requests.get(
                    f"{API_BASE_URL}/analytics/aar/{session_id}",
                    timeout=DEFAULT_TIMEOUT,
                )
                if resp.status_code == 200:
                    aar = resp.json()
                    st.session_state["aar_data"] = aar
                else:
                    st.error(f"No existing AAR found (HTTP {resp.status_code}). Try generating one.")
            except requests.exceptions.RequestException:
                st.error("Network error: could not reach the API server.")
            except Exception as e:
                st.error(f"Error fetching AAR: {e}")

    # Use cached AAR data if neither button was just clicked
    if aar is None and not generate_clicked and not view_clicked:
        aar = st.session_state.get("aar_data")

    # --- Display AAR ---
    if aar:
        st.markdown("---")

        # Grade Display
        grade = aar.get("overall_grade", "N/A")
        gc = GRADE_COLORS.get(grade, "#95a5a6")
        st.markdown(
            f"<div style='text-align:center;padding:20px;'>"
            f"<span style='font-size:72px;font-weight:bold;color:{gc};'>{grade}</span>"
            f"<br><span style='font-size:18px;color:#aaa;'>Overall Grade</span></div>",
            unsafe_allow_html=True,
        )

        # Summary
        st.markdown("---")
        st.markdown("### Summary")
        st.markdown(aar.get("summary", "No summary available."))
        if aar.get("ai_feedback"):
            st.info(f"**AI Feedback:** {aar['ai_feedback']}")

        # Timeline Visualization
        st.markdown("---")
        st.markdown("### Decision Timeline")
        timeline = aar.get("timeline_analysis", [])
        if timeline:
            for decision in timeline:
                action = decision.get("action", "Unknown action")
                score = decision.get("quality_score", 0)
                impact = decision.get("impact", "neutral")
                category = decision.get("category", "general")

                with st.expander(
                    f"{_score_icon(score)} {action[:80]} — Score: {score}/100",
                    expanded=False,
                ):
                    col_info, col_score = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**Action:** {action}")
                        if decision.get("timestamp"):
                            st.caption(f"Timestamp: {decision['timestamp']}")
                        if decision.get("context"):
                            st.caption(f"Context: {decision['context']}")
                    with col_score:
                        st.markdown(f"**Impact:** {IMPACT_LABELS.get(impact, '⚪ Unknown')}")
                        st.markdown(
                            f"<span style='background:#333;padding:3px 8px;"
                            f"border-radius:4px;font-size:12px;'>{category}</span>",
                            unsafe_allow_html=True,
                        )
                    st.progress(score / 100, text=f"Quality: {score}/100")
                    if decision.get("reasoning"):
                        st.markdown(f"**Reasoning:** {decision['reasoning']}")
                    if decision.get("better_alternative"):
                        st.warning(f"**Better Alternative:** {decision['better_alternative']}")
        else:
            st.info("No timeline decisions recorded for this session.")

        # Alternative Paths
        st.markdown("---")
        st.markdown("### Alternative Paths")
        alt_paths = aar.get("alternative_paths", [])
        if alt_paths:
            for alt in alt_paths:
                col_left, col_right = st.columns([3, 1])
                with col_left:
                    st.markdown(f"**Decision Point:** {alt.get('decision_point', 'N/A')}")
                    st.markdown(f"**Original Action:** {alt.get('original_action', 'N/A')}")
                    st.markdown(f"**Suggested Action:** {alt.get('suggested_action', 'N/A')}")
                    st.markdown(f"**Expected Outcome:** {alt.get('expected_outcome', 'N/A')}")
                with col_right:
                    diff = alt.get("difficulty", "medium")
                    st.markdown(f"**Difficulty:** {DIFFICULTY_LABELS.get(diff, '⚪ Unknown')}")
                st.markdown("---")
        else:
            st.info("No alternative paths suggested.")

        # Strengths & Weaknesses
        st.markdown("### Strengths & Weaknesses")
        col_str, col_weak = st.columns(2)
        with col_str:
            st.markdown("#### Strengths")
            strengths = aar.get("strengths", [])
            if strengths:
                for s in strengths:
                    st.markdown(f"- {s}")
            else:
                st.info("No strengths identified.")
        with col_weak:
            st.markdown("#### Weaknesses")
            weaknesses = aar.get("weaknesses", [])
            if weaknesses:
                for w in weaknesses:
                    st.markdown(f"- {w}")
            else:
                st.info("No weaknesses identified.")

        # Recommendations
        st.markdown("---")
        st.markdown("### Training Recommendations")
        recommendations = aar.get("recommendations", [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"{i}. {rec}")
        else:
            st.info("No recommendations available.")

        # Score Breakdown Chart
        st.markdown("---")
        st.markdown("### Score Breakdown")
        score_breakdown = aar.get("score_breakdown", {})
        metrics = aar.get("metrics", {})
        chart_data = score_breakdown or metrics

        if chart_data:
            categories = list(chart_data.keys())
            values = list(chart_data.values())
            is_breakdown = bool(score_breakdown)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=categories,
                        y=values,
                        marker_color=[("#2ecc71" if v >= 0 else "#e74c3c") for v in values]
                        if is_breakdown
                        else "#3498db",
                        text=[f"{v:+d}" if isinstance(v, int) and is_breakdown else f"{v}" for v in values],
                        textposition="outside",
                    )
                ]
            )
            fig.update_layout(
                title="Points by Category" if is_breakdown else "Performance Metrics",
                xaxis_title="Category" if is_breakdown else "Metric",
                yaxis_title="Points" if is_breakdown else "Value",
                template="plotly_dark",
                height=350,
                margin=dict(t=40, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No score breakdown data available.")

        # Export Buttons
        st.markdown("---")
        st.markdown("### Export Data")
        col_json, col_csv = st.columns(2)

        with col_json:
            if st.button("Export JSON", use_container_width=True):
                try:
                    resp = requests.get(
                        f"{API_BASE_URL}/analytics/export/json/{session_id}",
                        timeout=DEFAULT_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        import json

                        st.download_button(
                            label="Download JSON",
                            data=json.dumps(resp.json(), indent=2),
                            file_name=f"aar_{session_id}.json",
                            mime="application/json",
                            use_container_width=True,
                        )
                    else:
                        st.error(f"Export failed (HTTP {resp.status_code})")
                except requests.exceptions.RequestException:
                    st.error("Network error during export.")
                except Exception as e:
                    st.error(f"Export error: {e}")

        with col_csv:
            if st.button("Export CSV", use_container_width=True):
                try:
                    resp = requests.get(
                        f"{API_BASE_URL}/analytics/export/csv/{session_id}",
                        timeout=DEFAULT_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        st.download_button(
                            label="Download CSV",
                            data=resp.text,
                            file_name=f"aar_{session_id}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    else:
                        st.error(f"Export failed (HTTP {resp.status_code})")
                except requests.exceptions.RequestException:
                    st.error("Network error during export.")
                except Exception as e:
                    st.error(f"Export error: {e}")

# Sidebar Navigation
with st.sidebar:
    st.markdown("## Navigation")
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")
    if st.button("🎮 War Game", use_container_width=True):
        st.switch_page("pages/2_War_Game.py")
    if st.button("📋 Scenario Builder", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")
    if st.button("📂 Session Manager", use_container_width=True):
        st.switch_page("pages/4_Session_Manager.py")
    st.markdown("---")
    st.markdown("## About AAR")
    st.markdown("""
    The After Action Review evaluates your
    incident response performance across
    multiple dimensions:

    - **Timeline Analysis** — Each decision
      scored for quality and impact
    - **Alternative Paths** — What you could
      have done differently
    - **Score Breakdown** — Points by category
    - **Recommendations** — Targeted training
      areas for improvement
    """)
