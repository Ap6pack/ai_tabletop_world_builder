#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Streamlit Executive Dashboard - C-suite business impact visibility.

Full-page dashboard showing stock impact, customer churn, regulatory risk,
media exposure, notification obligations, and recovery projections.
Works in both single-player and multi-team exercise modes.
"""
import streamlit as st
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

st.set_page_config(page_title="Executive Dashboard", page_icon="📊", layout="wide")

st.title("📊 Executive Business Impact Dashboard")
st.markdown("C-suite visibility into incident costs, regulatory exposure, and recovery timelines")
st.markdown("---")

# Determine data source: active game session or exercise
game_state = st.session_state.get("game_state")
exercise_id = st.session_state.get("exercise_id")

if not game_state and exercise_id:
    # Try loading from exercise
    try:
        resp = requests.get(
            f"{API_BASE_URL}/exercise/{exercise_id}/state",
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code == 200:
            state = resp.json()
            game_state = state.get("game_state")
    except requests.ConnectionError:
        pass

if not game_state:
    st.warning(
        "No active game session or exercise found. "
        "Start a War Game or join an Exercise first."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎮 War Game", use_container_width=True):
            st.switch_page("pages/2_War_Game.py")
    with col2:
        if st.button("🏗️ Exercise Setup", use_container_width=True):
            st.switch_page("pages/10_Exercise_Setup.py")
    st.stop()

# Extract data
org = game_state.get("organization", {})
impact = game_state.get("business_impact") or {}
exec_metrics = impact.get("executive_metrics") or {}

org_name = org.get("name", "Unknown Organization")
industry = org.get("industry", "Unknown")

# --- Hero Metrics ---
st.markdown(f"### {org_name} — {industry}")

m1, m2, m3, m4 = st.columns(4)
with m1:
    total_cost = impact.get("total_cost", 0)
    st.metric(
        "Total Financial Impact",
        f"${total_cost:,.0f}",
        delta=f"-${total_cost:,.0f}" if total_cost > 0 else None,
        delta_color="inverse",
    )
with m2:
    stock_pct = exec_metrics.get("stock_price_impact_pct", 0)
    st.metric(
        "Stock Price Impact",
        f"{stock_pct:+.1f}%",
        delta=f"{stock_pct:.1f}%" if stock_pct != 0 else None,
        delta_color="inverse",
    )
with m3:
    churn = exec_metrics.get("customer_churn_rate", 0)
    st.metric(
        "Customer Churn Risk",
        f"{churn:.1f}%",
        delta=f"+{churn:.1f}%" if churn > 0 else None,
        delta_color="inverse",
    )
with m4:
    risk_level = exec_metrics.get("regulatory_risk_level", "low")
    risk_colors = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
    st.metric("Regulatory Risk", f"{risk_colors.get(risk_level, '')} {risk_level.upper()}")

st.markdown("---")

# --- Cost Breakdown ---
left_col, right_col = st.columns([3, 2])

with left_col:
    st.markdown("### 💰 Financial Impact Breakdown")
    downtime_cost = impact.get("downtime_cost", 0)
    data_loss_cost = impact.get("data_loss_cost", 0)
    reputation_damage = impact.get("reputation_damage", 0)
    compliance_penalties = impact.get("compliance_penalties", {})
    compliance_total = sum(compliance_penalties.values()) if isinstance(compliance_penalties, dict) else 0

    if PLOTLY_AVAILABLE and total_cost > 0:
        labels = ["Downtime", "Data Loss", "Compliance", "Reputation"]
        values = [downtime_cost, data_loss_cost, compliance_total, reputation_damage]
        colors = ["#FF6B6B", "#FFA07A", "#FFD700", "#87CEEB"]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors,
            textinfo="label+percent",
        )])
        fig.update_layout(
            title="Cost Distribution",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Fallback text display
        st.markdown(f"- **Downtime Costs:** ${downtime_cost:,.0f}")
        st.markdown(f"- **Data Loss Costs:** ${data_loss_cost:,.0f}")
        st.markdown(f"- **Compliance Penalties:** ${compliance_total:,.0f}")
        st.markdown(f"- **Reputation Damage:** ${reputation_damage:,.0f}")

        if compliance_penalties:
            st.markdown("**Penalty Breakdown:**")
            for framework, amount in compliance_penalties.items():
                st.markdown(f"  - {framework}: ${amount:,.0f}")

with right_col:
    st.markdown("### 📈 Key Indicators")

    # Media exposure
    media = exec_metrics.get("media_exposure_level", "none")
    media_icons = {"none": "⚪", "local": "🔵", "national": "🟠", "international": "🔴"}
    st.markdown(f"**Media Exposure:** {media_icons.get(media, '')} {media.title()}")

    # Recovery time
    recovery_days = exec_metrics.get("estimated_recovery_time_days", 0)
    st.markdown(f"**Estimated Recovery:** {recovery_days} days")

    # Records compromised
    records = impact.get("records_compromised", 0)
    st.markdown(f"**Records Compromised:** {records:,}")

    # Downtime
    downtime_hours = impact.get("downtime_hours", 0)
    st.markdown(f"**System Downtime:** {downtime_hours:.1f} hours")

    # Board and SEC
    board_required = exec_metrics.get("board_notification_required", False)
    sec_required = exec_metrics.get("sec_disclosure_required", False)

    if board_required:
        st.error("🔴 **Board Notification Required**")
    if sec_required:
        st.error("🔴 **SEC 8-K Disclosure Required**")

st.markdown("---")

# --- Notification Obligations ---
st.markdown("### 📋 Regulatory Notification Obligations")
obligations = exec_metrics.get("notification_obligations", [])
if obligations:
    for i, obligation in enumerate(obligations):
        st.checkbox(obligation, key=f"obligation_{i}")
else:
    st.success("No regulatory notification obligations identified at this time.")

st.markdown("---")

# --- Incident Timeline (Key Events) ---
st.markdown("### ⏱️ Key Decision Points")
timeline = game_state.get("incident_timeline", [])
if timeline:
    # Show only critical/high severity events and player actions
    key_events = [
        e for e in timeline
        if e.get("severity") in ("critical", "high") or e.get("actor") == "player"
    ]
    if key_events:
        for event in key_events[-15:]:
            sev = event.get("severity", "info")
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(sev, "⚪")
            actor = event.get("actor", "system")
            actor_tag = "👤" if actor == "player" else "⚡"
            st.markdown(
                f"{icon} {actor_tag} **{event.get('event_type', '').title()}** — "
                f"{event.get('description', '')}"
            )
    else:
        st.info("No critical events recorded yet.")
else:
    st.info("No timeline events yet.")

# --- Game Score Summary ---
st.markdown("---")
score_col, status_col = st.columns(2)
with score_col:
    st.metric("Response Score", game_state.get("score", 0))
with status_col:
    status = game_state.get("status", "unknown")
    status_icon = {"in-progress": "🟡", "completed": "🟢", "failed": "🔴"}.get(status, "⚪")
    st.metric("Game Status", f"{status_icon} {status.title()}")

# Refresh button
if game_state.get("status") == "in-progress":
    if st.button("🔄 Refresh Dashboard"):
        st.rerun()
