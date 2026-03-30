"""
应用包初始化

注意：项目已迁移到 FastAPI，入口文件为 main_fastapi.py
此文件保留以维持向后兼容的导入路径
"""

# 版本信息
__version__ = "1.0.0"

# 为了保持向后兼容，导出常用的类和函数
from app.config import config, Config
from app.extensions import get_embedder, get_chroma_client, get_qdrant_client, get_async_qdrant_client
from app.core.user_context import UserContext

__all__ = [
    "config",
    "Config", 
    "get_embedder",
    "get_chroma_client",
    "get_qdrant_client",
    "get_async_qdrant_client",
    "UserContext",
]
