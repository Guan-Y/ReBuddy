"""
知识库服务 - 独立的用户隔离知识库管理
"""

import json
import uuid
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.config import Config
from app.core.user_context import UserContext


class KnowledgeBaseService:
    """独立的知识库服务，提供用户隔离的知识库管理功能"""
    
    def __init__(self, user_id: str = None):
        """初始化知识库服务

        Args:
            user_id: 用户ID，如果为None则使用当前用户ID
        """
        # 1. 用户识别（与FileService保持一致）
        self.user_id = user_id or UserContext.get_current_user_id()

        # 2. 用户专属路径
        user_paths = Config.get_user_paths(self.user_id)
        self.user_root = user_paths['storage_root']

        # 3. 知识库专属路径（用户隔离）
        self.kb_root = self.user_root / "knowledge_bases"
        self.kb_root.mkdir(parents=True, exist_ok=True)

        # 4. 用户专属的索引文件
        self.index_file = self.kb_root / ".kb_index.json"

        # 5. 用户专属的锁（避免与FileService冲突）
        self.lock = threading.RLock()

        # 6. 文件级别的锁管理器（细粒度锁，支持并发上传）
        self.file_locks = {}  # {kb_id: {file_id: RLock}}
        self.file_locks_lock = threading.Lock()  # 保护 file_locks 字典的锁

        # 7. 初始化用户索引文件
        self._init_user_index()
    
    def _init_user_index(self):
        """初始化用户知识库索引文件"""
        with self.lock:
            if not self.index_file.exists():
                default_index = {
                    "user_id": self.user_id,
                    "knowledge_bases": [],
                    "last_updated": datetime.now().isoformat()
                }
                with open(self.index_file, "w", encoding="utf-8") as f:
                    json.dump(default_index, f, ensure_ascii=False, indent=2)

    def _get_file_lock(self, kb_id: str, file_id: str) -> threading.RLock:
        """获取文件级别的锁（细粒度锁，支持并发上传）

        Args:
            kb_id: 知识库ID
            file_id: 文件ID

        Returns:
            文件级别的 RLock
        """
        with self.file_locks_lock:
            # 确保知识库的锁字典存在
            if kb_id not in self.file_locks:
                self.file_locks[kb_id] = {}

            # 获取或创建文件级别的锁
            if file_id not in self.file_locks[kb_id]:
                self.file_locks[kb_id][file_id] = threading.RLock()

            return self.file_locks[kb_id][file_id]
    
    def _load_user_index(self) -> Dict:
        """加载用户知识库索引"""
        with self.lock:
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载用户知识库索引失败: {e}")
                return {
                    "user_id": self.user_id,
                    "knowledge_bases": [],
                    "last_updated": datetime.now().isoformat()
                }
    
    def _save_user_index(self, index_data: Dict):
        """保存用户知识库索引"""
        with self.lock:
            try:
                index_data["last_updated"] = datetime.now().isoformat()
                with open(self.index_file, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存用户知识库索引失败: {e}")
                raise
    
    def _load_kb_metadata(self, kb_id: str) -> Optional[Dict]:
        """加载知识库元数据"""
        kb_dir = self.kb_root / kb_id
        metadata_file = kb_dir / "metadata.json"
        
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载知识库元数据失败 {kb_id}: {e}")
            return None
    
    def _save_kb_metadata(self, kb_dir: Path, metadata: Dict):
        """保存知识库元数据"""
        metadata_file = kb_dir / "metadata.json"
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存知识库元数据失败: {e}")
            raise
    
    def _update_user_index(self, kb_metadata: Dict):
        """更新用户索引"""
        index_data = self._load_user_index()
        
        # 查找并更新或添加知识库
        kb_list = index_data["knowledge_bases"]
        existing_index = next((i for i, kb in enumerate(kb_list) if kb["id"] == kb_metadata["id"]), None)
        
        if existing_index is not None:
            kb_list[existing_index] = {
                "id": kb_metadata["id"],
                "name": kb_metadata["name"],
                "description": kb_metadata["description"],
                "created_at": kb_metadata["created_at"],
                "updated_at": kb_metadata["updated_at"],
                "file_count": kb_metadata["file_count"],
                "status": kb_metadata["status"]
            }
        else:
            kb_list.append({
                "id": kb_metadata["id"],
                "name": kb_metadata["name"],
                "description": kb_metadata["description"],
                "created_at": kb_metadata["created_at"],
                "updated_at": kb_metadata["updated_at"],
                "file_count": kb_metadata["file_count"],
                "status": kb_metadata["status"]
            })
        
        self._save_user_index(index_data)
    
    def create_knowledge_base(self, name: str, description: str = "") -> Dict:
        """创建知识库 - 独立实现，不使用文件服务
        
        Args:
            name: 知识库名称
            description: 知识库描述
            
        Returns:
            知识库元数据字典
            
        Raises:
            ValueError: 名称重复或无效
            Exception: 创建失败
        """
        with self.lock:
            # 验证名称
            if not name or not name.strip():
                raise ValueError("知识库名称不能为空")
            
            name = name.strip()
            
            # 检查名称重复
            index_data = self._load_user_index()
            for kb in index_data["knowledge_bases"]:
                if kb["name"] == name:
                    raise ValueError(f"知识库名称 '{name}' 已存在")
            
            # 生成知识库ID
            kb_id = str(uuid.uuid4())
            kb_dir = self.kb_root / kb_id
            
            # 创建目录结构
            kb_dir.mkdir(parents=True, exist_ok=True)
            (kb_dir / "files").mkdir(exist_ok=True)
            (kb_dir / ".vectors").mkdir(exist_ok=True)
            
            # 创建知识库元数据
            kb_metadata = {
                "id": kb_id,
                "user_id": self.user_id,
                "name": name,
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "file_count": 0,
                "status": "active",
                "files": []
            }
            
            # 保存知识库元数据
            self._save_kb_metadata(kb_dir, kb_metadata)
            
            # 更新用户索引
            self._update_user_index(kb_metadata)
            
            return kb_metadata
    
    def list_knowledge_bases(self) -> List[Dict]:
        """列出用户的所有知识库
        
        Returns:
            知识库列表
        """
        index_data = self._load_user_index()
        return index_data["knowledge_bases"].copy()
    
    def get_knowledge_base_detail(self, kb_id: str) -> Optional[Dict]:
        """获取知识库详情
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            知识库详细信息，如果不存在返回None
        """
        kb_metadata = self._load_kb_metadata(kb_id)
        if kb_metadata and kb_metadata.get("user_id") == self.user_id:
            return kb_metadata
        return None
    
    def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            删除是否成功
        """
        with self.lock:
            # 检查知识库是否存在
            kb_metadata = self._load_kb_metadata(kb_id)
            if not kb_metadata or kb_metadata.get("user_id") != self.user_id:
                raise ValueError("知识库不存在或无权限访问")
            
            # 删除知识库目录
            kb_dir = self.kb_root / kb_id
            try:
                shutil.rmtree(kb_dir)
            except Exception as e:
                print(f"删除知识库目录失败: {e}")
                raise
            
            # 更新用户索引（移除记录）
            index_data = self._load_user_index()
            index_data["knowledge_bases"] = [
                kb for kb in index_data["knowledge_bases"] 
                if kb["id"] != kb_id
            ]
            self._save_user_index(index_data)
            
            return True
    
    def add_file_to_knowledge_base(self, kb_id: str, file_info: Dict) -> Dict:
        """添加文件到知识库（使用文件级别的细粒度锁，支持并发上传）

        Args:
            kb_id: 知识库ID
            file_info: 文件信息字典

        Returns:
            文件记录字典
        """
        # 生成文件ID（用于获取文件级别的锁）
        file_id = str(uuid.uuid4())
        file_lock = self._get_file_lock(kb_id, file_id)

        with file_lock:
            # 检查知识库是否存在（使用全局锁读取，避免并发问题）
            kb_metadata = None
            with self.lock:
                kb_metadata = self.get_knowledge_base_detail(kb_id)

            if not kb_metadata:
                raise ValueError("知识库不存在")

            # 创建文件记录（添加status字段）
            file_record = {
                "id": file_id,
                "name": file_info["name"],
                "original_name": file_info.get("original_name", file_info["name"]),
                "size": file_info.get("size", 0),
                "type": file_info.get("type", "unknown"),
                "uploaded_at": datetime.now().isoformat(),
                "file_path": file_info.get("file_path", ""),  # 物理文件路径
                "relative_path": file_info.get("relative_path", ""),  # 相对路径
                "status": "uploading",  # 初始状态：上传中
                "chunk_count": 0,  # 文本片段数量
                "has_summary": False  # 是否有AI摘要
            }

            # 添加到知识库元数据（使用全局锁保护元数据修改）
            with self.lock:
                kb_metadata["files"].append(file_record)
                kb_metadata["file_count"] = len(kb_metadata["files"])
                kb_metadata["updated_at"] = datetime.now().isoformat()

                # 保存知识库元数据
                kb_dir = self.kb_root / kb_id
                self._save_kb_metadata(kb_dir, kb_metadata)

                # 更新用户索引
                self._update_user_index(kb_metadata)

            return file_record
    
    def get_knowledge_base_files(self, kb_id: str) -> List[Dict]:
        """获取知识库文件列表
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            文件列表
        """
        kb_metadata = self.get_knowledge_base_detail(kb_id)
        if kb_metadata:
            return kb_metadata.get("files", [])
        return []
    
    def remove_file_from_knowledge_base(self, kb_id: str, file_id: str) -> bool:
        """从知识库移除文件
        
        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            
        Returns:
            移除是否成功
        """
        with self.lock:
            # 检查知识库是否存在
            kb_metadata = self.get_knowledge_base_detail(kb_id)
            if not kb_metadata:
                raise ValueError("知识库不存在或无权限访问")
            
            # 查找并移除文件
            original_count = len(kb_metadata["files"])
            kb_metadata["files"] = [
                f for f in kb_metadata["files"] 
                if f["id"] != file_id
            ]
            
            if len(kb_metadata["files"]) == original_count:
                return False  # 文件不存在
            
            # 更新元数据
            kb_metadata["file_count"] = len(kb_metadata["files"])
            kb_metadata["updated_at"] = datetime.now().isoformat()
            
            # 保存知识库元数据
            kb_dir = self.kb_root / kb_id
            self._save_kb_metadata(kb_dir, kb_metadata)
            
            # 更新用户索引
            self._update_user_index(kb_metadata)
            
            return True
    
    def get_kb_file_path(self, kb_id: str, file_id: str) -> Optional[Path]:
        """获取知识库文件的存储路径
        
        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            
        Returns:
            文件路径，如果不存在返回None
        """
        kb_metadata = self.get_knowledge_base_detail(kb_id)
        if not kb_metadata:
            return None
        
        for file_record in kb_metadata.get("files", []):
            if file_record["id"] == file_id:
                return self.kb_root / kb_id / "files" / file_record["name"]
        
        return None
    
    def get_file_content(self, kb_id: str, file_id: str) -> Optional[bytes]:
        """获取文件完整内容
        
        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            
        Returns:
            文件二进制内容，如果文件不存在返回None
        """
        # 1. 获取文件物理路径
        file_path = self.get_kb_file_path(kb_id, file_id)
        if not file_path or not file_path.exists():
            return None
        
        # 2. 读取文件内容
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None
    
    def get_file_text_content(self, kb_id: str, file_id: str, encoding: str = 'utf-8') -> Optional[str]:
        """获取文件文本内容

        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            encoding: 文件编码，默认utf-8

        Returns:
            文件文本内容，如果读取失败返回None
        """
        # 1. 获取文件二进制内容
        binary_content = self.get_file_content(kb_id, file_id)
        if binary_content is None:
            return None

        # 2. 尝试解码为文本
        try:
            return binary_content.decode(encoding)
        except UnicodeDecodeError:
            # 尝试其他编码
            for alt_encoding in ['gbk', 'gb2312', 'latin1']:
                try:
                    return binary_content.decode(alt_encoding)
                except UnicodeDecodeError:
                    continue
            return None  # 所有编码都失败

    def update_file_status(self, kb_id: str, file_id: str, status: str, **kwargs) -> bool:
        """更新文件状态

        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            status: 新状态
            **kwargs: 其他可更新字段（如 chunk_count, has_summary, message）

        Returns:
            更新是否成功
        """
        with self.lock:
            # 检查知识库是否存在
            kb_metadata = self.get_knowledge_base_detail(kb_id)
            if not kb_metadata:
                return False

            # 查找并更新文件
            updated = False
            for file_record in kb_metadata.get("files", []):
                if file_record["id"] == file_id:
                    file_record["status"] = status
                    # 更新其他字段
                    for key, value in kwargs.items():
                        file_record[key] = value
                    updated = True
                    break

            if updated:
                # 保存知识库元数据
                kb_metadata["updated_at"] = datetime.now().isoformat()
                kb_dir = self.kb_root / kb_id
                self._save_kb_metadata(kb_dir, kb_metadata)

            return updated

    def get_file_status(self, kb_id: str, file_id: str) -> Optional[Dict]:
        """获取文件状态

        Args:
            kb_id: 知识库ID
            file_id: 文件ID

        Returns:
            文件状态信息，如果不存在返回None
        """
        kb_metadata = self.get_knowledge_base_detail(kb_id)
        if not kb_metadata:
            return None

        for file_record in kb_metadata.get("files", []):
            if file_record["id"] == file_id:
                return {
                    "file_id": file_id,
                    "status": file_record.get("status", "unknown"),
                    "chunk_count": file_record.get("chunk_count", 0),
                    "has_summary": file_record.get("has_summary", False)
                }

        return None

    def get_all_file_statuses(self, kb_id: str) -> List[Dict]:
        """获取知识库中所有文件的状态

        Args:
            kb_id: 知识库ID

        Returns:
            文件状态列表
        """
        kb_metadata = self.get_knowledge_base_detail(kb_id)
        if not kb_metadata:
            return []

        statuses = []
        for file_record in kb_metadata.get("files", []):
            statuses.append({
                "file_id": file_record["id"],
                "status": file_record.get("status", "unknown"),
                "chunk_count": file_record.get("chunk_count", 0),
                "has_summary": file_record.get("has_summary", False)
            })

        return statuses

    def get_file_info(self, kb_id: str, file_id: str) -> Optional[Dict]:
        """获取文件详细信息
        
        Args:
            kb_id: 知识库ID
            file_id: 文件ID
            
        Returns:
            文件信息字典，如果不存在返回None
        """
        kb_metadata = self.get_knowledge_base_detail(kb_id)
        if not kb_metadata:
            return None
        
        for file_record in kb_metadata.get("files", []):
            if file_record["id"] == file_id:
                # 添加物理路径信息
                file_path = self.get_kb_file_path(kb_id, file_id)
                file_info = file_record.copy()
                file_info["physical_path"] = str(file_path) if file_path else None
                file_info["exists"] = file_path.exists() if file_path else False
                return file_info
        
        return None


# 全局服务实例管理
_kb_services = {}
_kb_services_lock = threading.Lock()

def get_knowledge_base_service(user_id: str = None) -> KnowledgeBaseService:
    """获取知识库服务实例（用户隔离）
    
    Args:
        user_id: 用户ID，如果为None则使用当前用户ID
        
    Returns:
        KnowledgeBaseService实例
    """
    current_user_id = user_id or UserContext.get_current_user_id()
    
    with _kb_services_lock:
        if current_user_id not in _kb_services:
            _kb_services[current_user_id] = KnowledgeBaseService(current_user_id)
        return _kb_services[current_user_id]

def get_user_knowledge_base_service():
    """获取当前用户的知识库服务实例"""
    return get_knowledge_base_service()