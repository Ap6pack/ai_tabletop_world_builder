"""
Streamlit Settings Page - Configure platform settings.
"""
import streamlit as st
import requests

st.set_page_config(
    page_title="Settings",
    page_icon="",
    layout="wide"
)

st.title("Platform Settings")
st.markdown("Configure LLM providers, content policies, and system preferences")
st.markdown("---")

# LLM Provider Configuration
st.markdown("### LLM Provider Configuration")

provider = st.selectbox(
    "Select LLM Provider",
    ["OpenAI", "Anthropic", "Ollama (Local)"],
    help="Choose which AI provider to use for scenario generation and game narration"
)

col1, col2 = st.columns(2)

if provider == "OpenAI":
    with col1:
        api_key = st.text_input("OpenAI API Key", type="password", help="Get your API key from platform.openai.com")
        model = st.selectbox("Model", ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"])
    with col2:
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1, help="Higher = more creative, Lower = more deterministic")
        max_tokens = st.number_input("Max Tokens", 100, 8000, 2000, 100)

elif provider == "Anthropic":
    with col1:
        api_key = st.text_input("Anthropic API Key", type="password", help="Get your API key from console.anthropic.com")
        model = st.selectbox("Model", ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"])
    with col2:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        max_tokens = st.number_input("Max Tokens", 100, 8000, 4096, 100)

elif provider == "Ollama (Local)":
    with col1:
        base_url = st.text_input("Ollama Base URL", "http://localhost:11434", help="URL where Ollama is running")
        model = st.selectbox("Model", ["llama3", "llama2", "mistral", "mixtral"], help="Models must be pulled in Ollama first")
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
                "max_tokens": 10
            }

            # Add provider-specific config if entered
            if provider == "OpenAI" and api_key:
                test_payload["api_key"] = api_key
                test_payload["model"] = model
            elif provider == "Anthropic" and api_key:
                test_payload["api_key"] = api_key
                test_payload["model"] = model
            elif provider == "Ollama (Local)":
                test_payload["base_url"] = base_url
                test_payload["model"] = model

            # Call API test endpoint
            response = requests.post(
                "http://127.0.0.1:8000/llm/complete",
                json=test_payload,
                timeout=10
            )

            if response.status_code == 200:
                st.success("✅ Connection successful! Provider is working correctly.")
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                st.error(f"❌ Connection failed: {error_detail}")

        except requests.exceptions.Timeout:
            st.error("❌ Connection timeout - API took too long to respond")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API - make sure backend is running on http://127.0.0.1:8000")
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")

st.markdown("---")

# Content Policy Configuration
st.markdown("### Content Policy Settings")

policy_level = st.select_slider(
    "Content Policy Level",
    options=["Defensive", "Educational", "Advanced", "Unrestricted"],
    value="Educational",
    help="Control the level of detail in security scenarios"
)

# Display policy details
policies = {
    "Defensive": {
        "description": "Defensive security only - no offensive techniques",
        "suitable_for": "Beginner teams, compliance-sensitive environments",
        "includes": ["Security monitoring", "Incident response", "Security controls"],
        "excludes": ["Exploit code", "Offensive techniques", "Attack methods"]
    },
    "Educational": {
        "description": "Realistic scenarios with defensive focus",
        "suitable_for": "Training security teams, SOC analysts",
        "includes": ["Vulnerability identification", "Threat modeling", "Forensics"],
        "excludes": ["Actual exploit code", "Real credentials", "Weaponized malware"]
    },
    "Advanced": {
        "description": "Realistic attack/defense scenarios for experienced professionals",
        "suitable_for": "Advanced security teams, red/blue team exercises",
        "includes": ["Red team tactics", "Exploitation techniques", "APT analysis"],
        "excludes": ["Production-ready exploits", "Real attack coordination"]
    },
    "Unrestricted": {
        "description": "Full realism for advanced training (use with caution)",
        "suitable_for": "Expert security researchers, controlled environments",
        "includes": ["Realistic attacks", "Detailed exploitation", "Advanced TTPs"],
        "excludes": ["Illegal activities"]
    }
}

policy = policies[policy_level]

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Description:** {policy['description']}")
    st.markdown(f"**Suitable For:** {policy['suitable_for']}")
with col2:
    with st.expander("View Policy Details"):
        st.markdown("**Includes:**")
        for item in policy['includes']:
            st.markdown(f"- {item}")
        st.markdown("**Excludes:**")
        for item in policy['excludes']:
            st.markdown(f"- {item}")

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
        stats_response = requests.get("http://127.0.0.1:8000/settings/storage/stats", timeout=2)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            st.metric("Saved Scenarios", stats["saved_scenarios"])
            st.metric("Disk Usage", f"{stats['disk_usage_mb']} MB")
        else:
            st.metric("Saved Scenarios", "Error")
            st.metric("Disk Usage", "Error")
    except:
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
            "data_path": data_path
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
            response = requests.post(
                "http://127.0.0.1:8000/settings/update",
                json=update_payload,
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                st.session_state.llm_provider = provider
                st.session_state.content_policy = policy_level
                st.success(f"✅ Settings saved successfully! Updated: {', '.join(result['updated_keys'])}")
                st.info(result.get('note', ''))
            else:
                st.error(f"❌ Failed to save settings: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Failed to save settings: {str(e)}")

with col2:
    if st.button("Reset to Defaults", use_container_width=True):
        try:
            response = requests.post("http://127.0.0.1:8000/settings/reset/defaults", timeout=5)
            if response.status_code == 200:
                result = response.json()
                st.success("✅ " + result['message'])
                st.info(result.get('note', ''))
                st.rerun()
            else:
                st.error(f"❌ Failed to reset: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Failed to reset: {str(e)}")

with col3:
    if st.button("Export Config", use_container_width=True):
        try:
            response = requests.post("http://127.0.0.1:8000/settings/export", timeout=5)
            if response.status_code == 200:
                config_data = response.json()
                import json
                config_json = json.dumps(config_data, indent=2)
                st.download_button(
                    label="📥 Download Config",
                    data=config_json,
                    file_name="platform_config.json",
                    mime="application/json",
                    use_container_width=True
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
        health_response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if health_response.status_code == 200:
            st.success("✅ API Running")
        else:
            st.warning("⚠️ API Issues")
    except:
        st.error("❌ API Offline")

    # Check configured providers
    st.markdown("**Configured Providers**")
    try:
        providers_response = requests.get("http://127.0.0.1:8000/llm/providers", timeout=5)
        if providers_response.status_code == 200:
            providers = providers_response.json()
            available = [p for p, is_available in providers.items() if is_available]
            if available:
                st.success(f"✅ {len(available)} active: {', '.join(available)}")
            else:
                st.warning("⚠️ No providers configured")
        else:
            st.info("Unable to check providers")
    except:
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
                    response = requests.delete("http://127.0.0.1:8000/settings/data/clear", timeout=10)
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
