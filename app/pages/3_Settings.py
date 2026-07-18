#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Streamlit Settings Page - Configure platform settings.
"""

import requests
import streamlit as st

from config import API_BASE_URL, DEFAULT_TIMEOUT, HEALTH_CHECK_TIMEOUT

st.set_page_config(page_title="Settings", page_icon="", layout="wide")

st.title("Platform Settings")
st.markdown("Configure LLM providers, content policies, and system preferences")
st.markdown("---")

# LLM Provider Configuration
st.markdown("### LLM Provider Configuration")

# Check current provider status
try:
    providers_response = requests.get(f"{API_BASE_URL}/llm/providers", timeout=DEFAULT_TIMEOUT)
    current_providers = {}
    if providers_response.status_code == 200:
        current_providers = providers_response.json()
except Exception:
    current_providers = {}

provider = st.selectbox(
    "Select LLM Provider",
    ["OpenAI", "Anthropic", "Together", "Ollama (Local)"],
    help="Choose which AI provider to use for scenario generation and game narration",
)

col1, col2 = st.columns(2)

if provider == "OpenAI":
    with col1:
        # Show current status
        is_configured = current_providers.get("openai", False)
        if is_configured:
            st.success("✅ API Key Configured")
            if st.button("🗑️ Clear API Key", key="clear_openai", help="Remove OpenAI API key"):
                if "confirm_clear_openai" not in st.session_state:
                    st.session_state.confirm_clear_openai = True
                    st.warning("⚠️ Click again to confirm removal")
                    st.rerun()
                else:
                    try:
                        response = requests.delete(
                            f"{API_BASE_URL}/settings/provider/openai/key", timeout=DEFAULT_TIMEOUT
                        )
                        if response.status_code == 200:
                            st.success("✅ OpenAI API key removed")
                            st.session_state.confirm_clear_openai = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error')}")
                            st.session_state.confirm_clear_openai = False
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state.confirm_clear_openai = False
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="Currently configured",
                help="Get your API key from platform.openai.com",
            )
        else:
            st.info("ℹ️ No API Key Configured")
            api_key = st.text_input("OpenAI API Key", type="password", help="Get your API key from platform.openai.com")

        model = st.selectbox("Model", ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"])
    with col2:
        temperature = st.slider(
            "Temperature", 0.0, 2.0, 0.7, 0.1, help="Higher = more creative, Lower = more deterministic"
        )
        max_tokens = st.number_input("Max Tokens", 100, 8000, 2000, 100)

elif provider == "Anthropic":
    with col1:
        # Show current status
        is_configured = current_providers.get("anthropic", False)
        if is_configured:
            st.success("✅ API Key Configured")
            if st.button("🗑️ Clear API Key", key="clear_anthropic", help="Remove Anthropic API key"):
                if "confirm_clear_anthropic" not in st.session_state:
                    st.session_state.confirm_clear_anthropic = True
                    st.warning("⚠️ Click again to confirm removal")
                    st.rerun()
                else:
                    try:
                        response = requests.delete(
                            f"{API_BASE_URL}/settings/provider/anthropic/key", timeout=DEFAULT_TIMEOUT
                        )
                        if response.status_code == 200:
                            st.success("✅ Anthropic API key removed")
                            st.session_state.confirm_clear_anthropic = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error')}")
                            st.session_state.confirm_clear_anthropic = False
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state.confirm_clear_anthropic = False
            api_key = st.text_input(
                "Anthropic API Key",
                type="password",
                placeholder="Currently configured",
                help="Get your API key from console.anthropic.com",
            )
        else:
            st.info("ℹ️ No API Key Configured")
            api_key = st.text_input(
                "Anthropic API Key", type="password", help="Get your API key from console.anthropic.com"
            )

        model = st.selectbox(
            "Model", ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
        )
    with col2:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        max_tokens = st.number_input("Max Tokens", 100, 8000, 4096, 100)

elif provider == "Together":
    with col1:
        # Show current status
        is_configured = current_providers.get("together", False)
        if is_configured:
            st.success("✅ API Key Configured")
            if st.button("🗑️ Clear API Key", key="clear_together", help="Remove Together API key"):
                if "confirm_clear_together" not in st.session_state:
                    st.session_state.confirm_clear_together = True
                    st.warning("⚠️ Click again to confirm removal")
                    st.rerun()
                else:
                    try:
                        response = requests.delete(
                            f"{API_BASE_URL}/settings/provider/together/key", timeout=DEFAULT_TIMEOUT
                        )
                        if response.status_code == 200:
                            st.success("✅ Together API key removed")
                            st.session_state.confirm_clear_together = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error')}")
                            st.session_state.confirm_clear_together = False
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state.confirm_clear_together = False
            api_key = st.text_input(
                "Together API Key",
                type="password",
                placeholder="Currently configured",
                help="Get your API key from api.together.xyz",
            )
        else:
            st.info("ℹ️ No API Key Configured")
            api_key = st.text_input("Together API Key", type="password", help="Get your API key from api.together.xyz")

        model = st.selectbox(
            "Model",
            [
                "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
            ],
        )
    with col2:
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
        max_tokens = st.number_input("Max Tokens", 100, 8000, 2000, 100)

elif provider == "Ollama (Local)":
    with col1:
        base_url = st.text_input("Ollama Base URL", "http://localhost:11434", help="URL where Ollama is running")
        model = st.selectbox(
            "Model", ["llama3", "llama2", "mistral", "mixtral"], help="Models must be pulled in Ollama first"
        )
    with col2:
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
        st.info("ℹMake sure Ollama is running and the model is pulled: `ollama pull llama3`")

# Test connection
if st.button("🔍 Test Connection", type="primary"):
    with st.spinner("Testing connection..."):
        try:
            # Build test payload based on selected provider
            test_payload = {
                "prompt": "Say 'OK' if you can read this.",
                "provider": provider.lower().replace(" (local)", ""),
                "max_tokens": 10,
            }

            # Add provider-specific config if entered
            if provider in ("OpenAI", "Anthropic", "Together") and api_key:
                test_payload["api_key"] = api_key
                test_payload["model"] = model
            elif provider == "Ollama (Local)":
                test_payload["base_url"] = base_url
                test_payload["model"] = model

            # Call API test endpoint
            response = requests.post(f"{API_BASE_URL}/llm/complete", json=test_payload, timeout=10)

            if response.status_code == 200:
                st.success("✅ Connection successful! Provider is working correctly.")
            else:
                error_detail = response.json().get("detail", "Unknown error")
                st.error(f"❌ Connection failed: {error_detail}")

        except requests.exceptions.Timeout:
            st.error("❌ Connection timeout - API took too long to respond")
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to API - make sure backend is running on {API_BASE_URL}")
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")

st.markdown("---")

# Content Policy Configuration
st.markdown("### Content Policy Settings")

policy_level = st.select_slider(
    "Content Policy Level",
    options=["Defensive", "Educational", "Advanced", "Unrestricted"],
    value="Educational",
    help="Control the level of detail in security scenarios",
)

# Display policy details
policies = {
    "Defensive": {
        "description": "Defensive security only - no offensive techniques",
        "suitable_for": "Beginner teams, compliance-sensitive environments",
        "includes": ["Security monitoring", "Incident response", "Security controls"],
        "excludes": ["Exploit code", "Offensive techniques", "Attack methods"],
    },
    "Educational": {
        "description": "Realistic scenarios with defensive focus",
        "suitable_for": "Training security teams, SOC analysts",
        "includes": ["Vulnerability identification", "Threat modeling", "Forensics"],
        "excludes": ["Actual exploit code", "Real credentials", "Weaponized malware"],
    },
    "Advanced": {
        "description": "Realistic attack/defense scenarios for experienced professionals",
        "suitable_for": "Advanced security teams, red/blue team exercises",
        "includes": ["Red team tactics", "Exploitation techniques", "APT analysis"],
        "excludes": ["Production-ready exploits", "Real attack coordination"],
    },
    "Unrestricted": {
        "description": "Full realism for advanced training (use with caution)",
        "suitable_for": "Expert security researchers, controlled environments",
        "includes": ["Realistic attacks", "Detailed exploitation", "Advanced TTPs"],
        "excludes": ["Illegal activities"],
    },
}

policy = policies[policy_level]

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Description:** {policy['description']}")
    st.markdown(f"**Suitable For:** {policy['suitable_for']}")
with col2, st.expander("View Policy Details"):
    st.markdown("**Includes:**")
    for item in policy["includes"]:
        st.markdown(f"- {item}")
    st.markdown("**Excludes:**")
    for item in policy["excludes"]:
        st.markdown(f"- {item}")

st.markdown("---")

# Content Policy & Safety Configuration
st.markdown("### Content Policy & Safety Configuration")
st.markdown("Advanced safety features with filtering, validation, and audit logging.")

# Initialize session state for safety settings
if "enable_action_filtering" not in st.session_state:
    st.session_state.enable_action_filtering = True
if "enable_content_validation" not in st.session_state:
    st.session_state.enable_content_validation = True
if "enable_audit_logging" not in st.session_state:
    st.session_state.enable_audit_logging = True

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Content Filtering**")
    enable_action_filtering = st.checkbox(
        "Enable Pre-Action Content Filtering",
        value=st.session_state.enable_action_filtering,
        help="Filter player actions before processing to detect policy violations",
    )
    enable_content_validation = st.checkbox(
        "Enable Post-Generation Validation",
        value=st.session_state.enable_content_validation,
        help="Validate AI-generated content before delivery to players",
    )

    st.markdown("**Filter Categories**")
    enable_credential_detection = st.checkbox("Detect Credentials (API keys, passwords)", value=True)
    enable_pii_detection = st.checkbox("Detect PII (emails, SSNs, phone numbers)", value=True)
    enable_exploit_detection = st.checkbox("Detect Exploit Code (SQL injection, XSS)", value=True)
    enable_sensitive_detection = st.checkbox("Detect Sensitive Info (IPs, secrets)", value=True)

    redaction_style = st.selectbox(
        "Redaction Style",
        options=["mask", "remove", "replace"],
        index=0,
        help="How to redact violations: mask=[REDACTED], remove=delete, replace=safe text",
    )

with col2:
    st.markdown("**Audit Logging**")
    enable_audit_logging = st.checkbox(
        "Enable Audit Logging",
        value=st.session_state.enable_audit_logging,
        help="Log all policy checks, violations, and safety events for compliance",
    )
    audit_retention_days = st.slider(
        "Audit Log Retention (days)",
        min_value=7,
        max_value=365,
        value=90,
        step=7,
        help="How long to keep audit logs before automatic cleanup",
    )

    st.markdown("**Violation Handling**")
    violation_escalation_threshold = st.slider(
        "Escalation Threshold (violations)",
        min_value=1,
        max_value=5,
        value=2,
        help="Number of violations before escalating to admin review",
    )
    violation_time_window = st.slider(
        "Violation Time Window (hours)",
        min_value=1,
        max_value=72,
        value=24,
        help="Time window for counting repeat violations",
    )

# Audit Log Viewer
st.markdown("---")
st.markdown("### Audit Log Viewer")

col1, col2, col3 = st.columns(3)

with col1:
    log_event_type = st.selectbox(
        "Event Type", options=["all", "policy_check", "violation", "filter", "sanitization"], index=0
    )

with col2:
    log_severity = st.selectbox("Severity", options=["all", "info", "warning", "error", "critical"], index=0)

with col3:
    log_limit = st.number_input("Max Logs", min_value=10, max_value=500, value=50, step=10)

if st.button("Load Audit Logs", use_container_width=True):
    try:
        # Build query parameters
        params = {"limit": log_limit}
        if log_event_type != "all":
            params["event_type"] = log_event_type
        if log_severity != "all":
            params["severity"] = log_severity

        response = requests.get(f"{API_BASE_URL}/audit/logs", params=params, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 200:
            logs = response.json()
            if logs:
                st.success(f"✅ Loaded {len(logs)} audit logs")

                # Display logs in a table
                import pandas as pd

                df = pd.DataFrame(logs)

                # Format timestamp for display
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

                # Select columns to display
                display_columns = ["timestamp", "event_type", "severity", "result", "violations"]
                available_columns = [col for col in display_columns if col in df.columns]

                st.dataframe(df[available_columns], use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs found matching the filters")
        else:
            st.error(f"❌ Failed to load logs: {response.json().get('detail', 'Unknown error')}")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API request failed: {str(e)}")
    except Exception as e:
        st.error(f"❌ Error loading logs: {str(e)}")

# Compliance Reporting
st.markdown("---")
st.markdown("### Compliance Reporting")

col1, col2, col3 = st.columns(3)

with col1:
    report_start_date = st.date_input("Start Date", value=None)

with col2:
    report_end_date = st.date_input("End Date", value=None)

with col3:
    report_format = st.selectbox("Format", options=["json", "csv"], index=0)

if st.button("Generate Compliance Report", use_container_width=True):
    if not report_start_date or not report_end_date:
        st.warning("⚠️ Please select both start and end dates")
    elif report_start_date > report_end_date:
        st.error("❌ Start date must be before end date")
    else:
        try:
            params = {"start_date": report_start_date.isoformat(), "end_date": report_end_date.isoformat()}

            response = requests.get(f"{API_BASE_URL}/audit/compliance-report", params=params, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                report = response.json()

                st.success("✅ Compliance report generated")

                # Display key metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Checks", report.get("total_checks", 0))

                with col2:
                    st.metric("Total Violations", report.get("total_violations", 0))

                with col3:
                    violation_rate = report.get("violation_rate", 0)
                    st.metric("Violation Rate", f"{violation_rate}%")

                with col4:
                    # Calculate severity level based on violation rate
                    if violation_rate < 5:
                        severity_indicator = "🟢 Low"
                    elif violation_rate < 15:
                        severity_indicator = "🟡 Medium"
                    else:
                        severity_indicator = "🔴 High"
                    st.metric("Risk Level", severity_indicator)

                # Violations by type
                if report.get("violations_by_type"):
                    st.markdown("**Violations by Type**")
                    violations_df = pd.DataFrame(list(report["violations_by_type"].items()), columns=["Type", "Count"])
                    st.dataframe(violations_df, use_container_width=True, hide_index=True)

                # Violations by severity
                if report.get("violations_by_severity"):
                    st.markdown("**Violations by Severity**")
                    severity_df = pd.DataFrame(
                        list(report["violations_by_severity"].items()), columns=["Severity", "Count"]
                    )
                    st.dataframe(severity_df, use_container_width=True, hide_index=True)

                # Top violation patterns
                if report.get("top_violation_patterns"):
                    st.markdown("**Top Violation Patterns**")
                    patterns_df = pd.DataFrame(report["top_violation_patterns"])
                    st.dataframe(patterns_df, use_container_width=True, hide_index=True)

                # Export report
                import json

                if report_format == "json":
                    report_data = json.dumps(report, indent=2)
                    mime_type = "application/json"
                    file_ext = "json"
                else:  # CSV
                    # Convert report to CSV format (simplified)
                    csv_lines = [
                        "Metric,Value",
                        f"Total Checks,{report.get('total_checks', 0)}",
                        f"Total Violations,{report.get('total_violations', 0)}",
                        f"Violation Rate,{report.get('violation_rate', 0)}%",
                    ]
                    report_data = "\n".join(csv_lines)
                    mime_type = "text/csv"
                    file_ext = "csv"

                st.download_button(
                    label=f"📥 Download Report ({report_format.upper()})",
                    data=report_data,
                    file_name=f"compliance_report_{report_start_date}_{report_end_date}.{file_ext}",
                    mime=mime_type,
                    use_container_width=True,
                )
            else:
                st.error(f"❌ Failed to generate report: {response.json().get('detail', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ API request failed: {str(e)}")
        except Exception as e:
            st.error(f"❌ Error generating report: {str(e)}")

st.markdown("---")

# Session Configuration
st.markdown("### Session Settings")

col1, col2 = st.columns(2)

with col1:
    session_timeout = st.number_input("Session Timeout (minutes)", 15, 480, 60, 15)
    max_context = st.number_input("Max Context Length (tokens)", 1000, 8000, 4000, 500)

with col2:
    auto_save = st.checkbox("Auto-save progress", value=True)
    show_hints = st.checkbox("Enable hints system", value=True)

st.markdown("---")

# Storage Configuration
st.markdown("### Storage Settings")

col1, col2 = st.columns(2)

with col1:
    scenarios_path = st.text_input("Scenarios Path", "./scenarios/generated")
    data_path = st.text_input("Data Path", "./data")

with col2:
    st.markdown("**Storage Statistics**")
    try:
        stats_response = requests.get(f"{API_BASE_URL}/settings/storage/stats", timeout=HEALTH_CHECK_TIMEOUT)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            st.metric("Saved Scenarios", stats["saved_scenarios"])
            st.metric("Disk Usage", f"{stats['disk_usage_mb']} MB")
        else:
            st.metric("Saved Scenarios", "Error")
            st.metric("Disk Usage", "Error")
    except requests.exceptions.RequestException:
        st.metric("Saved Scenarios", "Unavailable")
        st.metric("Disk Usage", "Unavailable")

st.markdown("---")

# Save settings
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("Save Settings", use_container_width=True, type="primary"):
        # Build update payload
        update_payload = {
            "default_llm_provider": provider.lower().replace(" (local)", ""),
            "default_content_policy": policy_level.lower(),
            "session_timeout": session_timeout * 60,  # Convert minutes to seconds
            "max_context_length": max_context,
            "scenarios_path": scenarios_path,
            "data_path": data_path,
            # Phase 4: Safety & Policy settings
            "enable_action_filtering": enable_action_filtering,
            "enable_content_validation": enable_content_validation,
            "enable_audit_logging": enable_audit_logging,
            "enable_credential_detection": enable_credential_detection,
            "enable_pii_detection": enable_pii_detection,
            "enable_exploit_detection": enable_exploit_detection,
            "enable_sensitive_detection": enable_sensitive_detection,
            "redaction_style": redaction_style,
            "audit_retention_days": audit_retention_days,
            "violation_escalation_threshold": violation_escalation_threshold,
            "violation_time_window": violation_time_window,
        }

        # Add provider-specific settings
        if provider == "OpenAI" and api_key:
            update_payload["openai_api_key"] = api_key
            update_payload["openai_model"] = model
            update_payload["openai_temperature"] = temperature
        elif provider == "Anthropic" and api_key:
            update_payload["anthropic_api_key"] = api_key
            update_payload["anthropic_model"] = model
            update_payload["anthropic_temperature"] = temperature
        elif provider == "Ollama (Local)":
            update_payload["ollama_base_url"] = base_url
            update_payload["ollama_model"] = model
            update_payload["ollama_temperature"] = temperature

        try:
            response = requests.post(f"{API_BASE_URL}/settings/update", json=update_payload, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                result = response.json()
                st.session_state.llm_provider = provider
                st.session_state.content_policy = policy_level
                st.success(f"✅ Settings saved successfully! Updated: {', '.join(result['updated_keys'])}")
                st.info(result.get("note", ""))
            else:
                st.error(f"❌ Failed to save settings: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Failed to save settings: {str(e)}")

with col2:
    if st.button("Reset to Defaults", use_container_width=True):
        try:
            response = requests.post(f"{API_BASE_URL}/settings/reset/defaults", timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                result = response.json()
                st.success("✅ " + result["message"])
                st.info(result.get("note", ""))
                st.rerun()
            else:
                st.error(f"❌ Failed to reset: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Failed to reset: {str(e)}")

with col3:
    if st.button("Export Config", use_container_width=True):
        try:
            response = requests.post(f"{API_BASE_URL}/settings/export", timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                config_data = response.json()
                import json

                config_json = json.dumps(config_data, indent=2)
                st.download_button(
                    label="📥 Download Config",
                    data=config_json,
                    file_name="platform_config.json",
                    mime="application/json",
                    use_container_width=True,
                )
                st.success("✅ Config ready for download")
            else:
                st.error(f"❌ Failed to export: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Failed to export: {str(e)}")

# Sidebar
with st.sidebar:
    st.markdown("## System Information")

    # Check API status
    st.markdown("**API Status**")
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        if health_response.status_code == 200:
            st.success("✅ API Running")
        else:
            st.warning("⚠️ API Issues")
    except requests.exceptions.RequestException:
        st.error("❌ API Offline")

    # Check configured providers
    st.markdown("**Configured Providers**")
    try:
        providers_response = requests.get(f"{API_BASE_URL}/llm/providers", timeout=DEFAULT_TIMEOUT)
        if providers_response.status_code == 200:
            providers = providers_response.json()
            configured = [p for p, is_available in providers.items() if is_available]
            if configured:
                st.success(f"✅ {len(configured)} configured")
                for provider in configured:
                    st.caption(f"• {provider.capitalize()}")
                st.info("💡 To remove: Go to Settings → Clear API Key")
            else:
                st.warning("⚠️ No providers configured")
                st.caption("Add API keys in Settings to enable providers")
        else:
            st.info("Unable to check providers")
    except requests.exceptions.RequestException:
        st.info("Unable to check providers")

    st.markdown("---")

    st.markdown("## Quick Links")
    st.markdown("[Documentation](#)")
    st.markdown("[Report Issue](#)")
    st.markdown("[Community](#)")

    st.markdown("---")

    st.markdown("## Danger Zone")
    with st.expander("Advanced Actions"):
        st.warning("⚠️ These actions are destructive and cannot be undone!")

        if st.button("🗑️ Clear All Data", use_container_width=True, type="secondary"):
            # Add confirmation
            if "confirm_clear" not in st.session_state:
                st.session_state.confirm_clear = False

            if not st.session_state.confirm_clear:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion of all scenarios and sessions!")
                st.rerun()
            else:
                try:
                    response = requests.delete(f"{API_BASE_URL}/settings/data/clear", timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ {result['message']}")
                        st.session_state.confirm_clear = False
                    else:
                        st.error(f"❌ Failed: {response.json().get('detail', 'Unknown error')}")
                        st.session_state.confirm_clear = False
                except Exception as e:
                    st.error(f"❌ Failed: {str(e)}")
                    st.session_state.confirm_clear = False

        # Reset confirmation if user navigates away
        if st.session_state.get("confirm_clear") and st.button("Cancel", use_container_width=True):
            st.session_state.confirm_clear = False
            st.rerun()
