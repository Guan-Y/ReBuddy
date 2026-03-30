"""全局扩展管理"""
import chromadb
from sentence_transformers import SentenceTransformer
import torch
from qdrant_client import QdrantClient
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams


# 全局扩展实例
embedder = None

# ChromaDB客户端缓存 {path: client}
_chroma_clients = {}

# Qdrant客户端实例
_qdrant_client = None
_async_qdrant_client = None


# 全局初始化标志
_extensions_initialized = False


def init_extensions(app=None):
    """
    初始化所有扩展
    
    注意：app 参数已弃用，保留仅用于向后兼容
    """
    global embedder, _qdrant_client, _async_qdrant_client, _extensions_initialized
    
    # 避免重复初始化
    if _extensions_initialized:
        return embedder, _qdrant_client, _async_qdrant_client
    
    # 初始化Embedding模型
    if embedder is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        embedder = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    
    # 标记为已初始化
    _extensions_initialized = True
    
    return embedder, _qdrant_client, _async_qdrant_client


def get_chroma_client(user_id=None, persist_directory=None):
    """
    获取ChromaDB客户端
    Args:
        user_id: 用户ID，如果提供则使用用户专属路径
        persist_directory: 直接指定持久化目录，优先于user_id
    Returns:
        ChromaDB客户端实例
    """
    # 确定持久化路径
    if persist_directory is None:
        if user_id is not None:
            from app.config import Config
            user_paths = Config.get_user_paths(user_id)
            persist_directory = user_paths['vector_db_path']
        else:
            from app.config import Config
            persist_directory = Config.VECTOR_DB_PATH
    
    # 使用缓存避免重复创建客户端
    if persist_directory not in _chroma_clients:
        _chroma_clients[persist_directory] = chromadb.PersistentClient(path=persist_directory)
    
    return _chroma_clients[persist_directory]


def get_embedder():
    """获取Embedding模型，如果未初始化则尝试自动初始化"""
    global embedder
    
    if embedder is None:
        # 尝试自动初始化
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            embedder = SentenceTransformer('all-MiniLM-L6-v2', device=device)
            print(f"✅ Embedding模型自动初始化成功，设备: {device.upper()}")
        except Exception as e:
            print(f"⚠️ Embedding模型自动初始化失败: {e}")
            return None
    
    return embedder


def get_qdrant_client():
    """获取同步Qdrant客户端，如果未初始化则尝试自动初始化"""
    global _qdrant_client
    
    if _qdrant_client is None:
        # 尝试自动初始化
        try:
            from app.config import Config
            import os
            
            # 确保Qdrant存储路径存在
            os.makedirs(Config.QDRANT_STORAGE_PATH, exist_ok=True)
            
            if Config.QDRANT_USE_IN_MEMORY:
                # 内存模式（用于测试）
                _qdrant_client = QdrantClient(":memory:")
                print(f"✅ Qdrant内存模式客户端自动初始化成功")
            else:
                # 持久化模式
                if Config.QDRANT_HOST == "localhost":
                    # 本地持久化模式
                    _qdrant_client = QdrantClient(path=Config.QDRANT_STORAGE_PATH)
                    print(f"✅ Qdrant本地持久化客户端自动初始化成功: {Config.QDRANT_STORAGE_PATH}")
                else:
                    # 远程服务器模式
                    _qdrant_client = QdrantClient(
                        host=Config.QDRANT_HOST,
                        port=Config.QDRANT_PORT,
                        api_key=Config.QDRANT_API_KEY,
                        timeout=Config.QDRANT_TIMEOUT,
                    )
                    print(f"✅ Qdrant远程客户端自动初始化成功: {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
                    
            # 标记扩展已初始化
            global _extensions_initialized
            _extensions_initialized = True
            
        except Exception as e:
            print(f"⚠️ Qdrant客户端自动初始化失败: {e}")
            return None
    
    return _qdrant_client


def get_async_qdrant_client():
    """获取异步Qdrant客户端"""
    return _async_qdrant_client
