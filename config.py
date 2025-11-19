"""Configuration settings for Taidi card game tracker."""

# Database settings
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