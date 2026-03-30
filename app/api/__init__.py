"""
FastAPI路由模块
"""

from .chat_routes import router as chat_router
from .file_routes import router as file_router
from .paper_routes import router as paper_router
from .system_routes import router as system_router
from .conversation_routes import router as conversation_router
from .user_routes import router as user_router
from .knowledge_routes import router as knowledge_router

__all__ = [
    "chat_router",
    "file_router", 
    "paper_router",
    "system_router",
    "conversation_router",
    "user_router",
    "knowledge_router"
]