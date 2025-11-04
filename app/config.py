"""
Frontend application configuration.
"""
import os

# API Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# Default timeouts (in seconds)
DEFAULT_TIMEOUT = 5
HEALTH_CHECK_TIMEOUT = 2
LONG_OPERATION_TIMEOUT = 30

# Application Settings
APP_TITLE = "Cybersecurity War Gaming Platform"
APP_VERSION = "0.4.0"
APP_ICON = ""
