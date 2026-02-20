"""CORS configuration module for FastAPI."""

from config.settings import settings

DEFAULTS = ["http://localhost:8501", "http://localhost:3000"]


def get_cors_origins() -> list:
    """Return allowed CORS origins from settings or defaults.

    Parses comma-separated origins from settings.cors_origins if available,
    otherwise returns defaults for Streamlit (8501) and Grafana (3000).
    """
    raw = getattr(settings, "cors_origins", None)
    if raw and isinstance(raw, str):
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return DEFAULTS
