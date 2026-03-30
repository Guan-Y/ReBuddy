"""
用户上下文管理 - 处理多用户会话和存储隔离

注意：已移除 Flask 依赖，当前使用简化版本
"""
import uuid
from typing import Optional

from app.config import Config


class UserContext:
    """用户上下文管理器"""
    
    # 类级别的默认用户ID（用于单用户模式）
    _default_user_id: Optional[str] = None
    
    @staticmethod
    def get_current_user_id() -> str:
        """
        获取当前用户ID
        
        当前实现返回固定的默认用户ID（单用户模式）。
        如需多用户支持，可扩展为从请求头/JWT token 中获取
        """
        if UserContext._default_user_id is None:
            # 使用基于固定命名空间的确定性UUID
            UserContext._default_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "default_user"))
        return UserContext._default_user_id
    
    @staticmethod
    def set_current_user_id(user_id: str):
        """设置当前用户ID（用于多用户场景下的手动设置）"""
        UserContext._default_user_id = user_id
    
    @staticmethod
    def get_user_paths() -> dict:
        """获取当前用户的存储路径"""
        user_id = UserContext.get_current_user_id()
        return Config.get_user_paths(user_id)
    
    @staticmethod
    def clear_user_context():
        """清除用户上下文"""
        UserContext._default_user_id = None


def init_user_context(app=None):
    """
    初始化用户上下文中间件
    
    注意：此函数已弃用，保留仅用于向后兼容。
    在 FastAPI 中，用户上下文通过依赖注入或中间件处理
    """
    pass
