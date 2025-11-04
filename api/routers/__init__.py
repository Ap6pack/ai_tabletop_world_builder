"""API routers module."""
from .llm import router as llm_router
from .content_policy import router as content_policy_router
from .scenarios import router as scenarios_router
from .game import router as game_router
from .settings import router as settings_router

__all__ = [
    "llm_router",
    "content_policy_router",
    "scenarios_router",
    "game_router",
    "settings_router",
]
