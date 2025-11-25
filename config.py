"""Configuration settings for Taidi card game tracker."""

import os

# Database settings - Turso (cloud) or SQLite (local)
USE_TURSO = os.getenv("STREAMLIT_SHARING_MODE") is not None or os.getenv("USE_TURSO") == "true"

if USE_TURSO:
    # Use Turso (cloud database) - secrets will be loaded at runtime
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'turso' in st.secrets:
            TURSO_DATABASE_URL = st.secrets["turso"]["database_url"]
            TURSO_AUTH_TOKEN = st.secrets["turso"]["auth_token"]
        else:
            # Fallback for local testing
            USE_TURSO = False
            DATABASE_PATH = "taidi_game.db"
    except:
        # Fallback if secrets not configured
        USE_TURSO = False
        DATABASE_PATH = "taidi_game.db"
else:
    # Use local SQLite (for development)
    DATABASE_PATH = "taidi_game.db"

# App settings
APP_TITLE = "🃏 Taidi Card Game Tracker"
DEFAULT_CARD_VALUE = 0.20
DEFAULT_PLAYERS = []

# UI settings
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATETIME_DISPLAY_FORMAT = "%Y-%m-%d %H:%M"

# Authentication settings
ENABLE_PASSWORD_PROTECTION = True
# Change this password to something secure!
APP_PASSWORD = "weijiangruinmylife"  # TODO: Change this password!

# Future: Multi-user support (not yet implemented)
ENABLE_MULTI_USER = False