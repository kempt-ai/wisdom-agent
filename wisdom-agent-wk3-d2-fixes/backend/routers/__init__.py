"""
Wisdom Agent API Routers

FastAPI routers for all API endpoints.
"""

from backend.routers.chat import router as chat_router
from backend.routers.memory import router as memory_router
from backend.routers.projects import router as projects_router
from backend.routers.files import router as files_router
from backend.routers.pedagogy import router as pedagogy_router
from backend.routers.reflection import router as reflection_router

__all__ = [
    "chat_router", 
    "memory_router",
    "projects_router",
    "files_router",
    "pedagogy_router",
    "reflection_router",
]
