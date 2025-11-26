"""Configuration settings for Taidi card game tracker."""

import os

# Database settings - Try to use Turso if secrets are available
USE_TURSO = False
TURSO_DATABASE_URL = None
TURSO_AUTH_TOKEN = None

# Try to load Turso secrets (works in Streamlit Cloud)
try:
    import streamlit as st
    if hasattr(st, 'secrets') and 'turso' in st.secrets:
        TURSO_DATABASE_URL = st.secrets["turso"]["database_url"]
        TURSO_AUTH_TOKEN = st.secrets["turso"]["auth_token"]
        USE_TURSO = True
        print("✅ Turso credentials loaded from secrets")
except Exception as e:
    print(f"⚠️ Turso secrets not found: {e}")
    pass

# Fallback to local SQLite for development
if not USE_TURSO:
    DATABASE_PATH = "taidi_game.db"
    print("⚠️ Using local SQLite database")

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