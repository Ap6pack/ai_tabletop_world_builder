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
    st.metric("Saved Scenarios", "0")
    st.metric("Disk Usage", "0 MB")

st.markdown("---")

# Save settings
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("Save Settings", use_container_width=True, type="primary"):
        # TODO: Save settings to config
        st.session_state.llm_provider = provider
        st.session_state.content_policy = policy_level
        st.success("Settings saved successfully!")

with col2:
    if st.button("Reset to Defaults", use_container_width=True):
        st.info("Settings reset to defaults")
        st.rerun()

with col3:
    if st.button("Export Config", use_container_width=True):
        st.info("Config export coming soon")

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
        if st.button("Clear All Data", use_container_width=True):
            st.warning("This will delete all saved scenarios and game data!")
        if st.button("Reset Database", use_container_width=True):
            st.warning("This will reset all database tables!")
