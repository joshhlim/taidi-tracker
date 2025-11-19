"""Authentication module for Taidi card game tracker.

Current: Simple password protection for single group
Future: Can be extended to multi-user with accounts
"""

import streamlit as st
from config import ENABLE_PASSWORD_PROTECTION, APP_PASSWORD, ENABLE_MULTI_USER


def check_authentication() -> bool:
    """
    Check if user is authenticated.
    Returns True if authenticated, False otherwise.
    
    Current: Simple password check
    Future: Will support user accounts and sessions
    """
    if not ENABLE_PASSWORD_PROTECTION:
        return True
    
    # Check if already authenticated in this session
    if st.session_state.get("authenticated", False):
        return True
    
    return False


def login_form():
    """
    Display login form and handle authentication.
    
    Current: Single password for the group
    Future: Username + password for individual users
    """
    st.markdown("### 🔒 Login Required")
    st.markdown("Please enter the password to access the Taidi Tracker.")
    
    if ENABLE_MULTI_USER:
        # Future: Multi-user login
        st.info("Multi-user mode is enabled but not yet implemented.")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            # TODO: Implement user authentication
            st.error("Multi-user authentication not yet implemented!")
    else:
        # Current: Simple password protection
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                if password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect password!")
        
        with col2:
            st.caption("Contact your group admin if you don't have the password.")


def logout():
    """
    Log out the current user.
    
    Current: Clear authentication flag
    Future: Clear user session data
    """
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]
    
    # Future: Clear user-specific session data
    if ENABLE_MULTI_USER:
        if "user_id" in st.session_state:
            del st.session_state["user_id"]
        if "username" in st.session_state:
            del st.session_state["username"]


def show_logout_button():
    """Display logout button in sidebar."""
    if ENABLE_PASSWORD_PROTECTION and st.session_state.get("authenticated", False):
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()


# Future: Functions for multi-user support (placeholders)

def create_user(username: str, password: str, group_id: str = None) -> bool:
    """
    Create a new user account.
    TODO: Implement when multi-user is enabled.
    """
    if not ENABLE_MULTI_USER:
        raise NotImplementedError("Multi-user mode is not enabled")
    # TODO: Hash password, store in database
    pass


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate a user and return user info.
    TODO: Implement when multi-user is enabled.
    """
    if not ENABLE_MULTI_USER:
        raise NotImplementedError("Multi-user mode is not enabled")
    # TODO: Verify credentials, return user data
    pass


def get_current_user_group() -> str:
    """
    Get the current user's group ID.
    TODO: Implement when multi-user is enabled.
    Returns None for single-group mode.
    """
    if not ENABLE_MULTI_USER:
        return None
    # TODO: Return user's group_id from session
    pass