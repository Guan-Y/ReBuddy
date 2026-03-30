"""
数据库实体定义
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserEntity(Base):
    """用户实体"""
    __tablename__ = "users"
    
    user_id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100))
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class ConversationEntity(Base):
    """对话实体"""
    __tablename__ = "conversations"
    
    conversation_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    paper_id = Column(String(36))
    title = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)  # 标识对话是否活跃
    window_position = Column(Integer, default=0)  # 窗口位置，用于排序
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MessageEntity(Base):
    """消息实体"""
    __tablename__ = "messages"
    
    message_id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False)  # user/assistant
    timestamp = Column(DateTime, default=datetime.utcnow)


class FileEntity(Base):
    """文件实体"""
    __tablename__ = "files"
    
    file_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    parent_id = Column(String(36))
    is_folder = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ParseTaskEntity(Base):
    """解析任务实体"""
    __tablename__ = "parse_tasks"
    
    task_id = Column(String(36), primary_key=True)
    file_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    status = Column(String(20), default="pending")
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)