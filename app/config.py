import os
from pathlib import Path


class Config:
    """统一配置管理"""
    
    # 基础路径
    BASE_DIR = Path(__file__).resolve().parent.parent
    STORAGE_ROOT = BASE_DIR / "storage" / "user_files"
    VECTOR_DB_PATH = BASE_DIR / "storage" / "vector_db"
    LOGS_PATH = BASE_DIR / "storage" / "logs"
    
    # 原有路径映射（保持兼容性）
    USER_FILES_ROOT = STORAGE_ROOT
    MEMORY_PATH = BASE_DIR / "storage" / ".memory"
    PARSED_PAPERS_PATH = MEMORY_PATH / "papers_parsed"
    
    # 多用户配置
    @classmethod
    def get_user_paths(cls, user_id: str):
        """根据用户ID获取用户专属路径"""
        user_storage_root = cls.STORAGE_ROOT / user_id
        # 向量数据库使用固定路径，不再按用户分离
        user_vector_db_path = cls.VECTOR_DB_PATH  # 固定路径
        user_memory_path = cls.MEMORY_PATH / user_id
        user_parsed_papers_path = user_memory_path / "papers_parsed"
        user_logs_path = cls.LOGS_PATH / user_id
        
        return {
            'storage_root': user_storage_root,
            'vector_db_path': user_vector_db_path,
            'memory_path': user_memory_path,
            'parsed_papers_path': user_parsed_papers_path,
            'logs_path': user_logs_path
        }
    
    # Qdrant配置
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
    QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "60"))
    
    # Qdrant持久化配置
    QDRANT_STORAGE_PATH = os.getenv("QDRANT_STORAGE_PATH", str(VECTOR_DB_PATH / "qdrant_storage"))
    QDRANT_USE_IN_MEMORY = os.getenv("QDRANT_USE_IN_MEMORY", "false").lower() == "true"
    
    # 集合配置
    QDRANT_COLLECTION_PREFIX = "academic_searcher"
    VECTOR_SIZE = 384  # 与现有embedding模型一致
    
    @classmethod
    def get_collection_name(cls) -> str:
        """获取统一的集合名称"""
        return f"{cls.QDRANT_COLLECTION_PREFIX}_papers"
    
    @classmethod
    def get_user_collection_name(cls, user_id: str = None) -> str:
        """获取集合名称（保持向后兼容）"""
        return cls.get_collection_name()
    
    @classmethod
    def get_global_collection_name(cls) -> str:
        """获取全局集合名称（向后兼容）"""
        return cls.get_collection_name()
    
    # 数据库选择配置
    USE_QDRANT = os.getenv("USE_QDRANT", "true").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "8f4b2e1d9a3c5e7b1d9a3c5e7b8f4b2e1d9a3c5e7b1d9a3c5e7b8f4b2e1d9a3c5e7")
    
    # LLM 配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
    MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-max")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
    
    # 其他API配置
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_API_BASE = os.getenv("OPENROUTER_API_BASE")
    IFLOW_API_KEY = os.getenv("IFLOW_API_KEY")
    IFLOW_API_BASE = os.getenv("IFLOW_API_BASE")
    
    # 搜索配置
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
    TAVILY_SEARCH_API_KEY = os.getenv("TAVILY_SEARCH_API_KEY")
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_EXTENSIONS = ['.pdf']
    
    # 后台任务配置
    PARSE_WORKERS = int(os.getenv("PARSE_WORKERS", "2"))
    PARSE_SEMAPHORE = int(os.getenv("PARSE_SEMAPHORE", "2"))
    
    # 浏览器配置
    BROWSER_VIEWPORT_SIZE = 1024 * 5
    BROWSER_TIMEOUT = 300
    
    @staticmethod
    def init_app(app):
        """应用初始化时调用"""
        # 创建必要的目录
        Config.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        Config.VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        Config.LOGS_PATH.mkdir(parents=True, exist_ok=True)
        Config.MEMORY_PATH.mkdir(parents=True, exist_ok=True)
        Config.PARSED_PAPERS_PATH.mkdir(parents=True, exist_ok=True)
        
        # 设置上传文件大小限制
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    VECTOR_DB_PATH = Config.BASE_DIR / "tests" / "test_vector_db"


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}