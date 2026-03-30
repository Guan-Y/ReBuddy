"""
对话管理服务 - 处理多对话窗口的逻辑
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from app.models.schemas import Conversation, ConversationCreateRequest, ConversationUpdateRequest, HistoryMessage
from app.core.user_context import UserContext
from app.config import Config
from app.core.conversation_manager import ConversationManager, get_conversation_manager


class ConversationService:
    """对话管理服务"""
    
    # 类级别的空对话缓存，确保多用户隔离
    _empty_conversation_cache = {}  # {user_id: conversation_id}
    
    def __init__(self, user_id: str = None):
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        
        # 用户专属存储路径
        user_paths = Config.get_user_paths(self.user_id)
        self.conversations_file = user_paths['memory_path'] / 'conversations.json'

        # 使用单例模式获取 ConversationManager 实例
        self.conversation_manager = get_conversation_manager(self.user_id)
        
        # 加载对话列表
        self.conversations: Dict[str, Conversation] = {}
    
    def find_empty_conversation(self) -> Optional[str]:
        """查找当前用户的空对话
        
        Returns:
            str: 空对话的ID，如果没有找到则返回None
        """
        try:
            # 1. 首先检查缓存
            cached_id = self._empty_conversation_cache.get(self.user_id)
            if cached_id:
                # 验证缓存的对话是否仍然存在且为空
                conversation = self.conversation_manager.get_conversation_by_id(cached_id)
                if conversation and self._is_conversation_empty(conversation):
                    return cached_id
                else:
                    # 缓存失效，清除
                    self._empty_conversation_cache.pop(self.user_id, None)
            
            # 2. 遍历所有对话查找空对话
            conversations = self.conversation_manager.get_conversations(include_deleted=False)
            
            for conversation in conversations:
                if self._is_conversation_empty(conversation):
                    # 找到空对话，缓存其ID
                    self._empty_conversation_cache[self.user_id] = conversation['id']
                    return conversation['id']
            
            # 3. 没有找到空对话
            return None
            
        except Exception as e:
            print(f"查找空对话时出错: {e}")
            return None
    
    def _is_conversation_empty(self, conversation: Dict) -> bool:
        """判断对话是否为空
        
        Args:
            conversation: 对话字典
            
        Returns:
            bool: 如果对话为空返回True，否则返回False
        """
        try:
            # 获取对话消息
            conversation = self.conversation_manager.get_conversation_by_id(conversation['id'])
            messages = conversation.get('messages', [])
            
            # 如果没有消息，认为是空对话
            if not messages:
                return True
            
            # 如果只有系统消息，也认为是空对话
            user_messages = [msg for msg in messages if msg.get('type') != 'system']
            return len(user_messages) == 0
            
        except Exception as e:
            print(f"判断对话是否为空时出错: {e}")
            return False
    
    def create_conversation(self, title: str = "新对话") -> Dict:
        """创建新的通用对话会话，优先复用空对话"""
        try:
            # 1. 查找现有的空对话
            empty_conversation_id = self.find_empty_conversation()
            
            if empty_conversation_id:
                # 找到空对话，直接返回
                conversation = self.conversation_manager.get_conversation_by_id(empty_conversation_id)
                return {
                    "status": "success",
                    "conversation": conversation,
                    "reused": True  # 标记为复用的对话
                }
            
            # 2. 没有空对话，创建新对话
            conversation = self.conversation_manager.create_conversation(title)
            
            # 3. 缓存新创建的空对话ID
            if conversation:
                self._empty_conversation_cache[self.user_id] = conversation['id']
            
            return {
                "status": "success",
                "conversation": conversation,
                "reused": False  # 标记为新创建的对话
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def delete_conversation(self, conversation_id: str) -> Dict:
        """删除对话会话"""
        try:
            success = self.conversation_manager.delete_conversation(conversation_id)
            return {
                "status": "success" if success else "error",
                "message": "删除成功" if success else "对话不存在"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_conversation_by_id(self, conversation_id: str) -> Dict:
        """通过对话ID获取对话"""
        try:
            conversation = self.conversation_manager.get_conversation_by_id(conversation_id)
            if conversation:
                return {
                    "status": "success",
                    "conversation": conversation
                }
            else:
                return {
                    "status": "error",
                    "message": "对话不存在"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_conversations(self, include_deleted: bool = False) -> Dict:
        """获取所有对话列表"""
        try:
            conversations = self.conversation_manager.get_conversations(include_deleted)
            return {
                "status": "success",
                "conversations": conversations,
                "count": len(conversations)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def update_conversation_title(self, conversation_id: str, title: str) -> Dict:
        """更新对话标题"""
        try:
            success = self.conversation_manager.update_conversation_title(conversation_id, title)
            return {
                "status": "success" if success else "error",
                "message": "更新成功" if success else "对话不存在"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_conversation_messages(self, conversation_id: str) -> Dict:
        """获取对话消息"""
        try:
            # import pdb; pdb.set_trace()  # --- IGNORE ---
            conversation = self.conversation_manager.get_conversation_by_id(conversation_id)
            if not conversation:
                return {
                    "status": "error",
                    "message": "对话不存在"
                }
            
            messages = conversation.get('messages', [])
            return {
                "status": "success",
                "messages": messages
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
        
    def get_conversation_history(self, paper_id: str = None) -> List[HistoryMessage]:
        """获取对话历史"""
        if paper_id:
            return self.conversation_manager.get_paper_history(paper_id)
        else:
            return self.conversation_manager.get_general_history()
    
    def clear_conversation(self, paper_id: str = None) -> bool:
        """清除对话历史"""
        if paper_id:
            return self.conversation_manager.clear_paper_conversation(paper_id)
        else:
            self.conversation_manager.general_history.clear()
            return True
    


# 延迟初始化全局服务实例
conversation_manager_service = None

def get_conversation_service(user_id: str = None):
    """获取对话管理服务实例（延迟初始化）"""
    global conversation_manager_service
    if conversation_manager_service is None:
        conversation_manager_service = ConversationService(user_id)
    return conversation_manager_service

def get_user_conversation_service():
    """获取当前用户的对话管理服务实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return ConversationService(user_id)