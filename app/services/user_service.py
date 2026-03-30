"""
用户服务 - 管理用户信息和认证
"""

from typing import Optional, Dict, List
import json
import os
from pathlib import Path
from datetime import datetime

from app.config import Config


class UserService:
    """用户管理服务"""
    
    def __init__(self):
        # 用户数据存储路径
        self.users_path = Config.BASE_DIR / "storage" / "users"
        self.users_path.mkdir(parents=True, exist_ok=True)
        
        # 用户列表文件
        self.users_list_path = self.users_path / "users.json"
        
        # 加载用户数据
        self.users = self._load_users()
    
    def _load_users(self) -> Dict:
        """加载用户数据"""
        if self.users_list_path.exists():
            try:
                with open(self.users_list_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {}
    
    def _save_users(self):
        """保存用户数据"""
        with open(self.users_list_path, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def create_user(self, username: str, display_name: str = None) -> Dict:
        """创建新用户"""
        if username in self.users:
            raise ValueError(f"用户名 '{username}' 已存在")
        
        user_id = username  # 使用用户名作为ID
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "display_name": display_name or username,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "is_active": True
        }
        
        # 保存用户信息
        self.users[user_id] = user_data
        self._save_users()
        
        # 初始化用户存储空间
        user_paths = Config.get_user_paths(user_id)
        for path_name, path_obj in user_paths.items():
            path_obj.mkdir(parents=True, exist_ok=True)
        
        return user_data
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        return self.users.get(user_id)
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户信息"""
        if user_id not in self.users:
            return False
        
        user_data = self.users[user_id]
        user_data.update(kwargs)
        user_data['updated_at'] = datetime.now().isoformat()
        
        self._save_users()
        return True
    
    def update_last_login(self, user_id: str):
        """更新最后登录时间"""
        self.update_user(user_id, last_login=datetime.now().isoformat())
    
    def list_users(self) -> List[Dict]:
        """列出所有用户"""
        return list(self.users.values())
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户（包括所有数据）"""
        if user_id not in self.users:
            return False
        
        # 删除用户数据
        del self.users[user_id]
        self._save_users()
        
        # 删除用户存储空间
        user_paths = Config.get_user_paths(user_id)
        for path_name, path_obj in user_paths.items():
            if path_obj.exists():
                import shutil
                shutil.rmtree(path_obj)
        
        return True


# 延迟初始化全局服务实例
user_service = None

def get_user_service():
    """获取用户服务实例（延迟初始化）"""
    global user_service
    if user_service is None:
        user_service = UserService()
    return user_service