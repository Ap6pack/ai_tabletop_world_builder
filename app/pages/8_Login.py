"""
Streamlit Login & Registration Page.
"""
import streamlit as st
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, DEFAULT_TIMEOUT

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

# Initialize session state
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None


def login(username: str, password: str) -> bool:
    """Authenticate user and store token."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data["access_token"]
            st.session_state.refresh_token = data.get("refresh_token", "")
            # Fetch user profile
            profile_resp = requests.get(
                f"{API_BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {data['access_token']}"},
                timeout=DEFAULT_TIMEOUT,
            )
            if profile_resp.status_code == 200:
                st.session_state.current_user = profile_resp.json()
            return True
        elif response.status_code == 401:
            st.error("Invalid username or password.")
        else:
            st.error(f"Login failed: {response.json().get('detail', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Make sure the backend is running.")
    except Exception as e:
        st.error(f"Login error: {str(e)}")
    return False


def register(username: str, email: str, password: str, display_name: str) -> bool:
    """Register a new user account."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "display_name": display_name,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code == 200:
            return True
        else:
            detail = response.json().get("detail", "Registration failed")
            st.error(f"Registration failed: {detail}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Make sure the backend is running.")
    except Exception as e:
        st.error(f"Registration error: {str(e)}")
    return False


def logout():
    """Clear authentication state."""
    st.session_state.auth_token = None
    st.session_state.current_user = None
    st.session_state.pop("refresh_token", None)


# --- Main Page ---

if st.session_state.current_user:
    # Logged in view
    user = st.session_state.current_user
    st.title(f"Welcome, {user.get('display_name') or user.get('username', 'User')}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Profile")
        st.markdown(f"**Username:** {user.get('username', 'N/A')}")
        st.markdown(f"**Email:** {user.get('email', 'N/A')}")
        st.markdown(f"**Role:** {user.get('role', 'user')}")
        if user.get("created_at"):
            st.markdown(f"**Joined:** {user['created_at'][:10]}")

    with col2:
        st.markdown("### Quick Actions")
        if st.button("🎮 Start War Game", use_container_width=True):
            st.switch_page("pages/2_War_Game.py")
        if st.button("📊 View Analytics", use_container_width=True):
            st.switch_page("pages/6_Analytics.py")
        if st.button("📋 Build Scenario", use_container_width=True):
            st.switch_page("pages/1_Scenario_Builder.py")

    st.markdown("---")

    # Change password section
    with st.expander("Change Password"):
        with st.form("change_password"):
            old_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")

            if st.form_submit_button("Update Password"):
                if new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                elif len(new_pw) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    try:
                        resp = requests.post(
                            f"{API_BASE_URL}/auth/change-password",
                            json={"old_password": old_pw, "new_password": new_pw},
                            headers={"Authorization": f"Bearer {st.session_state.auth_token}"},
                            timeout=DEFAULT_TIMEOUT,
                        )
                        if resp.status_code == 200:
                            st.success("Password updated successfully.")
                        else:
                            st.error(resp.json().get("detail", "Failed to update password."))
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    st.markdown("---")
    if st.button("Logout", use_container_width=True):
        logout()
        st.rerun()

else:
    # Login / Register view
    st.title("🔐 Login")
    st.markdown("Sign in to access your war gaming sessions and analytics.")
    st.markdown("---")

    tab1, tab2 = st.tabs(["Sign In", "Register"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Please enter both username and password.")
                elif login(username, password):
                    st.success("Login successful!")
                    st.rerun()

    with tab2:
        with st.form("register_form"):
            reg_username = st.text_input("Username", key="reg_user")
            reg_email = st.text_input("Email", key="reg_email")
            reg_display = st.text_input("Display Name (optional)", key="reg_display")
            reg_password = st.text_input("Password", type="password", key="reg_pass")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

            if st.form_submit_button("Create Account", use_container_width=True, type="primary"):
                if not reg_username or not reg_email or not reg_password:
                    st.error("Please fill in all required fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif register(reg_username, reg_email, reg_password, reg_display):
                    st.success("Account created! You can now sign in.")

# Sidebar
with st.sidebar:
    st.markdown("## Navigation")

    if st.button("🏠 Home", use_container_width=True, key="nav_home"):
        st.switch_page("Home.py")
    if st.button("🎮 War Game", use_container_width=True, key="nav_war"):
        st.switch_page("pages/2_War_Game.py")
    if st.button("📊 Analytics", use_container_width=True, key="nav_analytics"):
        st.switch_page("pages/6_Analytics.py")

    st.markdown("---")
    if st.session_state.current_user:
        st.info(f"Logged in as **{st.session_state.current_user.get('username', 'User')}**")
    else:
        st.info("Not logged in. Auth is optional — the platform works without an account.")
