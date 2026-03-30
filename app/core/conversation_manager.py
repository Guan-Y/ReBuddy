import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Generator


from app.models.schemas import ChatRequest, ChatStreamResponse, HistoryMessage


class ConversationManager:
    """对话管理器（单例模式）"""
    
    # 类变量，存储所有用户的实例
    _instances: Dict[str, 'ConversationManager'] = {}
    
    def __new__(cls, user_id: str = None):
        """单例模式的实现"""
        from app.core.user_context import UserContext
        
        # 获取用户ID
        target_user_id = user_id or UserContext.get_current_user_id()
        
        # 如果该用户的实例不存在，创建新实例
        if target_user_id not in cls._instances:
            instance = super(ConversationManager, cls).__new__(cls)
            cls._instances[target_user_id] = instance
        
        return cls._instances[target_user_id]
    
    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return
        
        # 用户专属存储路径
        from app.config import Config
        user_paths = Config.get_user_paths(self.user_id)
        self.conversation_file = user_paths['memory_path'] / 'conversations.json'
        
        # 加载历史对话
        self.general_history: List[HistoryMessage] = []
        self.paper_conversations: Dict[str, List[HistoryMessage]] = {}
        self.kb_conversations: Dict[str, Dict] = {}  # 知识库对话：{kb_id: conversation_data}
        self.file_conversations: Dict[str, List[HistoryMessage]] = {}  # 文件对话：{kb_id:file_id: history}
        
        # 会话管理 - 每个会话有唯一ID
        self.conversations: Dict[str, Dict] = {}  # {conversation_id: conversation_info}
        self._load_conversations()
        
        # 标记为已初始化
        self._initialized = True
    
    def get_general_history(self) -> List[HistoryMessage]:
        """获取通用对话历史"""
        return self.general_history
    
    def get_paper_history(self, paper_id: str) -> List[HistoryMessage]:
        """获取论文对话历史"""
        paper_history = self.paper_conversations.get(paper_id)
        if paper_history is None:
            return []
        else:
            return paper_history.get('history', [])
    
    def add_general_message(self, content: str, msg_type: str):
        """添加通用对话消息"""
        message = HistoryMessage(
            timestamp=datetime.now().isoformat(),
            content=content,
            type=msg_type
        )
        self.general_history.append(message)
        
        # 保持历史记录在合理范围内
        if len(self.general_history) > 50:
            self.general_history = self.general_history[-50:]
        
        # 保存对话
        self._save_conversations()
    
    def add_paper_message(self, paper_id: str, content: str, msg_type: str):
        """添加论文对话消息"""
        if paper_id not in self.paper_conversations:
            self.paper_conversations[paper_id] = []
        
        message = HistoryMessage(
            timestamp=datetime.now().isoformat(),
            content=content,
            type=msg_type
        )
        self.paper_conversations[paper_id].append(message)
        
        # 保持历史记录在合理范围内
        if len(self.paper_conversations[paper_id]) > 50:
            self.paper_conversations[paper_id] = self.paper_conversations[paper_id][-50:]
        
        # 保存对话
        self._save_conversations()
    
    def create_conversation(self, title: str = "新对话") -> Dict:
        """创建新的通用对话会话"""
        conversation_id = str(uuid.uuid4())
        
        conversation = {
            'id': conversation_id,
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': [],
            'status': 'active'  # active, archived, deleted
        }
        
        self.conversations[conversation_id] = conversation
        self._save_conversations()
        return conversation
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话会话"""
        if conversation_id in self.conversations:
            # 标记为删除而不是直接删除，保持数据完整性
            self.conversations[conversation_id]['status'] = 'deleted'
            self.conversations[conversation_id]['updated_at'] = datetime.now().isoformat()
            
            # 清除空对话缓存
            self._clear_empty_conversation_cache(conversation_id)
            
            self._save_conversations()
            return True
        return False
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict]:
        """通过对话ID获取对话"""
        conversation = self.conversations.get(conversation_id)
        if conversation and conversation['status'] != 'deleted':
            return conversation
        return None
    
    def get_conversations(self, include_deleted: bool = False) -> List[Dict]:
        """获取所有对话列表"""
        conversations = []
        for conv in self.conversations.values():
            if not include_deleted and conv['status'] == 'deleted':
                continue
            conversations.append(conv)
        
        # 按更新时间排序
        conversations.sort(key=lambda x: x['updated_at'], reverse=True)
        return conversations
    
    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """更新对话标题"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]['title'] = title
            self.conversations[conversation_id]['updated_at'] = datetime.now().isoformat()
            self._save_conversations()
            return True
        return False
    
    def add_message_to_conversation(self, conversation_id: str, content: str, msg_type: str) -> bool:
        """向对话添加消息"""
        if conversation_id not in self.conversations:
            return False
        
        message = HistoryMessage(
            timestamp=datetime.now().isoformat(),
            content=content,
            type=msg_type
        )
        
        self.conversations[conversation_id]['messages'].append(message.model_dump())
        self.conversations[conversation_id]['updated_at'] = datetime.now().isoformat()
        
        # 保持消息数量在合理范围内
        if len(self.conversations[conversation_id]['messages']) > 100:
            self.conversations[conversation_id]['messages'] = self.conversations[conversation_id]['messages'][-100:]
        
        # 清除空对话缓存（如果添加的是用户消息）
        if msg_type in ['user', 'assistant']:
            self._clear_empty_conversation_cache(conversation_id)
        
        self._save_conversations()
        return True
    
    def _clear_empty_conversation_cache(self, conversation_id: str):
        """清除空对话缓存"""
        try:
            from app.services.conversation_service import ConversationService
            
            # 如果当前对话ID在缓存中，清除它
            if conversation_id == ConversationService._empty_conversation_cache.get(self.user_id):
                ConversationService._empty_conversation_cache.pop(self.user_id, None)
                
        except Exception as e:
            print(f"清除空对话缓存时出错: {e}")
    
    def start_conversation(self, paper_id: str, paper_name: str) -> Dict:
        """开始新的论文对话会话（用完即弃，不进入会话管理）"""
        if paper_id not in self.paper_conversations:
            self.paper_conversations[paper_id] = {
                'paper_name': paper_name,
                'history': [],
                'created_at': datetime.now().isoformat()
            }
        return self.paper_conversations[paper_id]
    
    def end_conversation(self, paper_id: str) -> bool:
        """结束论文对话会话（用完即弃，直接删除）"""
        if paper_id in self.paper_conversations:
            del self.paper_conversations[paper_id]
            self._save_conversations()
            return True
        return False
    
    def get_conversation(self, paper_id: str) -> Optional[Dict]:
        """获取论文对话（保持向后兼容）"""
        return self.paper_conversations.get(paper_id)
    
    def clear_paper_conversation(self, paper_id: str) -> bool:
        """清除论文对话"""
        if paper_id in self.paper_conversations:
            del self.paper_conversations[paper_id]
            self._save_conversations()
            return True
        return False
    
    def get_kb_history(self, kb_id: str) -> List[HistoryMessage]:
        """获取知识库对话历史"""
        kb_history = self.kb_conversations.get(kb_id)
        if kb_history is None:
            return []
        else:
            return kb_history.get('history', [])
    
    def add_kb_message(self, kb_id: str, kb_name: str, content: str, msg_type: str):
        """添加知识库对话消息"""
        if kb_id not in self.kb_conversations:
            # 如果知识库对话不存在，创建新对话
            self.kb_conversations[kb_id] = {
                'kb_name': kb_name,
                'history': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        
        message = HistoryMessage(
            timestamp=datetime.now().isoformat(),
            content=content,
            type=msg_type
        )
        self.kb_conversations[kb_id]['history'].append(message)
        self.kb_conversations[kb_id]['updated_at'] = datetime.now().isoformat()
        
        # 保持历史记录在合理范围内
        if len(self.kb_conversations[kb_id]['history']) > 50:
            self.kb_conversations[kb_id]['history'] = self.kb_conversations[kb_id]['history'][-50:]
        
        # 保存对话
        self._save_conversations()
    
    def start_kb_conversation(self, kb_id: str, kb_name: str) -> Dict:
        """开始知识库对话（如果不存在则创建）"""
        if kb_id not in self.kb_conversations:
            self.kb_conversations[kb_id] = {
                'kb_name': kb_name,
                'history': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        return self.kb_conversations[kb_id]
    
    def end_kb_conversation(self, kb_id: str) -> bool:
        """结束知识库对话（可选）"""
        if kb_id in self.kb_conversations:
            del self.kb_conversations[kb_id]
            self._save_conversations()
            return True
        return False
    
    def clear_kb_conversation(self, kb_id: str) -> bool:
        """清除知识库对话"""
        if kb_id in self.kb_conversations:
            self.kb_conversations[kb_id]['history'] = []
            self.kb_conversations[kb_id]['updated_at'] = datetime.now().isoformat()
            self._save_conversations()
            return True
        return False

    # ==================== 文件级对话管理 ====================

    def get_file_history(self, kb_id: str, file_id: str) -> List[HistoryMessage]:
        """获取文件对话历史"""
        key = f"{kb_id}:{file_id}"
        return self.file_conversations.get(key, [])

    def add_file_message(self, kb_id: str, file_id: str, content: str, msg_type: str):
        """添加文件对话消息"""
        key = f"{kb_id}:{file_id}"
        if key not in self.file_conversations:
            self.file_conversations[key] = []

        message = HistoryMessage(
            timestamp=datetime.now().isoformat(),
            content=content,
            type=msg_type
        )
        self.file_conversations[key].append(message)
        self._save_conversations()

    def clear_file_conversation(self, kb_id: str, file_id: str) -> bool:
        """清除文件对话历史"""
        key = f"{kb_id}:{file_id}"
        if key in self.file_conversations:
            del self.file_conversations[key]
            self._save_conversations()
            return True
        return False
    
    def _load_conversations(self):
        """加载用户对话历史"""
        if self.conversation_file.exists():
            try:
                with open(self.conversation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 转换为HistoryMessage对象
                    general_data = data.get('general_history', [])
                    self.general_history = [
                        HistoryMessage(**msg) for msg in general_data
                    ]
                    
                    # 转换论文对话
                    self.paper_conversations = data.get('paper_conversations', {})
                    
                    # 转换知识库对话
                    kb_data = data.get('kb_conversations', {})
                    for kb_id, kb_conv in kb_data.items():
                        # 转换 history 中的消息为 HistoryMessage 对象
                        if 'history' in kb_conv and isinstance(kb_conv['history'], list):
                            kb_conv['history'] = [
                                HistoryMessage(**msg) for msg in kb_conv['history']
                            ]
                    self.kb_conversations = kb_data

                    # 加载文件对话
                    file_data = data.get('file_conversations', {})
                    for key, file_history in file_data.items():
                        self.file_conversations[key] = [
                            HistoryMessage(**msg) for msg in file_history
                        ]

                    # 加载新的会话数据
                    self.conversations = data.get('conversations', {})
                    
            except Exception as e:
                print(f"加载对话历史失败: {e}")
    
    def _save_conversations(self):
        """保存用户对话历史"""
        try:
            # 确保目录存在
            self.conversation_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换知识库对话为可序列化格式
            kb_conversations_serializable = {}
            for kb_id, kb_conv in self.kb_conversations.items():
                kb_conversations_serializable[kb_id] = {
                    'kb_name': kb_conv.get('kb_name', ''),
                    'created_at': kb_conv.get('created_at', ''),
                    'updated_at': kb_conv.get('updated_at', ''),
                    'history': [msg.model_dump() if hasattr(msg, 'model_dump') else msg
                              for msg in kb_conv.get('history', [])]
                }

            # 转换文件对话为可序列化格式
            file_conversations_serializable = {}
            for key, file_history in self.file_conversations.items():
                file_conversations_serializable[key] = [
                    msg.model_dump() if hasattr(msg, 'model_dump') else msg
                    for msg in file_history
                ]

            # 转换为可序列化格式
            data = {
                'general_history': [msg.model_dump() for msg in self.general_history],
                'paper_conversations': self.paper_conversations,
                'kb_conversations': kb_conversations_serializable,
                'file_conversations': file_conversations_serializable,
                'conversations': self.conversations  # 新增会话数据
            }
            
            with open(self.conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    @classmethod
    def get_instance(cls, user_id: str = None) -> 'ConversationManager':
        """获取指定用户的 ConversationManager 实例"""
        return cls(user_id)
    
    @classmethod
    def get_current_user_instance(cls) -> 'ConversationManager':
        """获取当前用户的 ConversationManager 实例"""
        from app.core.user_context import UserContext
        user_id = UserContext.get_current_user_id()
        return cls(user_id)
    
    @classmethod
    def clear_instance(cls, user_id: str = None):
        """清除指定用户的实例（主要用于测试或重置）"""
        from app.core.user_context import UserContext
        target_user_id = user_id or UserContext.get_current_user_id()
        if target_user_id in cls._instances:
            del cls._instances[target_user_id]
    
    @classmethod
    def clear_all_instances(cls):
        """清除所有实例（主要用于测试）"""
        cls._instances.clear()


# 便捷函数
def get_conversation_manager(user_id: str = None) -> ConversationManager:
    """获取 ConversationManager 实例的便捷函数"""
    return ConversationManager.get_instance(user_id)


def get_current_user_conversation_manager() -> ConversationManager:
    """获取当前用户的 ConversationManager 实例的便捷函数"""
    return ConversationManager.get_current_user_instance()