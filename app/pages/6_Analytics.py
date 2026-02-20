#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Streamlit Analytics Dashboard Page - Performance metrics and training insights.
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT

st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")

st.title("📊 Analytics Dashboard")
st.markdown("Performance metrics, score trends, and training recommendations")
st.markdown("---")


def fetch_dashboard_data():
    """Fetch the main dashboard data from the analytics API."""
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/dashboard", timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            return response.json(), None
        return None, f"Failed to load dashboard (HTTP {response.status_code})"
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API server. Is the backend running?"
    except requests.exceptions.Timeout:
        return None, "Request timed out. The API server may be overloaded."
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def fetch_score_trends(limit=20):
    """Fetch score trend data from the analytics API."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/analytics/trends",
            params={"metric": "score", "limit": limit},
            timeout=DEFAULT_TIMEOUT
        )
        if response.status_code == 200:
            return response.json(), None
        return None, f"Failed to load trends (HTTP {response.status_code})"
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def fetch_sessions():
    """Fetch session list from the game API."""
    try:
        response = requests.get(f"{API_BASE_URL}/game/sessions", timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            return response.json(), None
        return None, f"Failed to load sessions (HTTP {response.status_code})"
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


# Refresh button
col_refresh, col_spacer = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Fetch dashboard data
dashboard, dash_error = fetch_dashboard_data()

if dash_error:
    st.error(f"❌ {dash_error}")
    st.info("Make sure the API server is running and the analytics endpoints are available.")
    st.stop()

if not dashboard:
    st.warning("No analytics data available yet. Complete some war game sessions to see metrics.")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🎮 Go to War Game", use_container_width=True, type="primary"):
            st.switch_page("pages/2_War_Game.py")
    with col2:
        if st.button("📋 Go to Scenario Builder", use_container_width=True):
            st.switch_page("pages/1_Scenario_Builder.py")
    st.stop()

# ===== SECTION 1: Overview Metrics =====
st.markdown("### Key Metrics")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Sessions Completed", dashboard.get("sessions_completed", 0))
with col2:
    avg_score = dashboard.get("average_score", 0)
    st.metric("Average Score", f"{avg_score:.1f}" if isinstance(avg_score, float) else avg_score)
with col3:
    st.metric("Best Score", dashboard.get("best_score", 0))
with col4:
    play_time = dashboard.get("total_play_time_minutes", 0)
    st.metric("Total Play Time", f"{play_time / 60:.1f} hrs" if play_time >= 60 else f"{play_time} min")

st.markdown("---")

# ===== SECTION 2: Score Trend Chart =====
st.markdown("### Score Trend")

score_trend_points = dashboard.get("trends", {}).get("score", [])
if not score_trend_points:
    trend_response, trend_error = fetch_score_trends()
    if trend_response and not trend_error:
        score_trend_points = trend_response.get("data_points", [])

if score_trend_points:
    # Handle list-of-dicts or list-of-numbers
    if isinstance(score_trend_points[0], (int, float)):
        fig_trend = px.line(
            y=score_trend_points, markers=True,
            title="Score Over Recent Sessions",
            labels={"index": "Session", "value": "Score"}
        )
        fig_trend.update_layout(xaxis_title="Session", yaxis_title="Score")
    else:
        trend_df = pd.DataFrame(score_trend_points)
        x_col = next((c for c in ["session", "timestamp", "date", "index"] if c in trend_df.columns), None)
        y_col = next((c for c in ["score", "value"] if c in trend_df.columns), None)
        if x_col and y_col:
            fig_trend = px.line(
                trend_df, x=x_col, y=y_col, markers=True,
                title="Score Over Recent Sessions",
                labels={x_col: x_col.replace("_", " ").title(), y_col: "Score"}
            )
            fig_trend.update_layout(xaxis_title=x_col.replace("_", " ").title(),
                                    yaxis_title="Score", hovermode="x unified")
        else:
            fig_trend = None
    if fig_trend:
        st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("No score trend data available yet. Complete more sessions to see trends.")

st.markdown("---")

# ===== SECTION 3: Skill Radar Chart =====
st.markdown("### Performance Radar")

metrics_data = dashboard.get("metrics", [])
radar_categories = [
    "response_time", "containment_speed", "objectives_completed_pct",
    "detection_rate", "resource_efficiency", "financial_efficiency"
]
radar_labels = [
    "Response Time", "Containment Speed", "Objectives Completed",
    "Detection Rate", "Resource Efficiency", "Financial Efficiency"
]

radar_values = []
if isinstance(metrics_data, dict):
    radar_values = [metrics_data.get(cat, 0) for cat in radar_categories]
elif isinstance(metrics_data, list) and metrics_data:
    aggregated = {cat: [] for cat in radar_categories}
    for entry in metrics_data:
        if isinstance(entry, dict):
            metric_dict = entry.get("metrics", entry)
            for cat in radar_categories:
                val = metric_dict.get(cat)
                if val is not None:
                    aggregated[cat].append(val)
    radar_values = [sum(v) / len(v) if v else 0 for v in (aggregated[c] for c in radar_categories)]

if radar_values and any(v > 0 for v in radar_values):
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=radar_values + [radar_values[0]],
        theta=radar_labels + [radar_labels[0]],
        fill="toself", name="Performance", line=dict(color="#636EFA")
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, title="Skill Performance Across Categories"
    )
    st.plotly_chart(fig_radar, use_container_width=True)
else:
    st.info("No performance metrics available yet. Complete sessions to build your radar profile.")

st.markdown("---")

# ===== SECTION 4: Session Comparison Table =====
st.markdown("### Recent Sessions")

sessions_response, sessions_error = fetch_sessions()
if sessions_error:
    st.warning(f"Could not load session data: {sessions_error}")
elif sessions_response:
    sessions_list = sessions_response
    if isinstance(sessions_response, dict):
        sessions_list = sessions_response.get("sessions", [])
    if sessions_list:
        table_rows = []
        for session in sessions_list:
            table_rows.append({
                "Session ID": str(session.get("session_id", ""))[:12] + "...",
                "Organization": session.get("organization", "N/A"),
                "Score": session.get("score", 0),
                "Time (min)": session.get("time_elapsed", 0),
                "Status": session.get("status", "unknown").replace("_", " ").title(),
                "Role": session.get("player_role", "N/A").replace("-", " ").title()
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No sessions found. Start a war game to see session data here.")
else:
    st.info("No session data available.")

st.markdown("---")

# ===== SECTION 5: Skill Gaps =====
st.markdown("### Identified Skill Gaps")

skill_gaps = dashboard.get("skill_gaps", [])
if skill_gaps:
    for gap in skill_gaps:
        if isinstance(gap, str):
            st.markdown(f"- {gap}")
        elif isinstance(gap, dict):
            gap_name = gap.get("name", gap.get("skill", "Unknown"))
            gap_detail = gap.get("description", gap.get("detail", ""))
            severity = gap.get("severity", "medium")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
            st.markdown(f"{icon} **{gap_name}**")
            if gap_detail:
                st.caption(gap_detail)
else:
    st.success("No skill gaps identified. Keep training to maintain your edge!")

st.markdown("---")

# ===== SECTION 6: Recommendations =====
st.markdown("### Training Recommendations")

recommendations = dashboard.get("recommendations", [])
if recommendations:
    for i, rec in enumerate(recommendations, 1):
        if isinstance(rec, str):
            st.markdown(f"**{i}.** {rec}")
        elif isinstance(rec, dict):
            rec_title = rec.get("title", rec.get("name", f"Recommendation {i}"))
            rec_detail = rec.get("description", rec.get("detail", ""))
            priority = rec.get("priority", "medium")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "📌")
            st.markdown(f"{icon} **{rec_title}**")
            if rec_detail:
                st.caption(rec_detail)
else:
    st.info("Complete more sessions to receive personalized training recommendations.")

# ===== Sidebar Navigation =====
with st.sidebar:
    st.markdown("## Navigation")
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")
    if st.button("📋 Scenario Builder", use_container_width=True):
        st.switch_page("pages/1_Scenario_Builder.py")
    if st.button("🎮 War Game", use_container_width=True):
        st.switch_page("pages/2_War_Game.py")
    if st.button("⚙️ Settings", use_container_width=True):
        st.switch_page("pages/3_Settings.py")

    st.markdown("---")
    st.markdown("## About Analytics")
    st.markdown("""
    This dashboard tracks your performance
    across war game sessions and identifies
    areas for improvement.

    - **Score Trend** shows progress over time
    - **Radar Chart** highlights strengths
    - **Skill Gaps** pinpoint weaknesses
    - **Recommendations** guide next steps
    """)
