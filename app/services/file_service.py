"""
文件服务 - 从原FileManager重构
"""

import json
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


from werkzeug.utils import secure_filename

from app.config import Config
from app.models.schemas import FileNode
from app.core.user_context import UserContext



class FileService:
    """文件管理服务 - 纯服务逻辑，调用算法层"""
    
    def __init__(self, user_id: str = None):
        # 获取用户路径
        if user_id:
            self.user_id = user_id
            user_paths = Config.get_user_paths(user_id)
        else:
            # 使用当前用户
            self.user_id = UserContext.get_current_user_id()
            user_paths = UserContext.get_user_paths()
        
        self.storage_root = user_paths['storage_root']
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        # 元数据文件路径
        self.metadata_path = self.storage_root / '.metadata.json'
        
        # 初始化算法层实例
        from app.core.file_manager import FileManager
        self.file_manager = FileManager(self.storage_root, self.metadata_path)
        
        # 服务级别的锁
        self.lock = Lock()
    
    def _load_metadata(self) -> List[Dict]:
        """加载文件树元数据"""
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # 创建初始元数据
        initial_metadata = self._build_file_tree()
        self._save_metadata(initial_metadata)
        return initial_metadata
    
    def _save_metadata(self, metadata: List[Dict] = None):
        """保存元数据到文件"""
        with self.lock:
            data = metadata or self.metadata
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _build_file_tree(self) -> List[Dict]:
        """从文件系统扫描并构建文件树"""
        root_path = Path(self.storage_root).resolve()
        
        def scan_directory(current_path: Path) -> List[Dict]:
            """递归扫描目录"""
            nodes = []
            try:
                items = sorted(current_path.iterdir(), key=lambda p: p.name.lower())
                
                for item in items:
                    # 跳过隐藏文件和元数据
                    if item.name.startswith('.') or item.name == '.metadata.json':
                        continue
                    
                    if item.is_dir():
                        node = {
                            "id": f"folder_{uuid.uuid4().hex[:8]}",
                            "name": item.name,
                            "type": "folder",
                            "path": item.relative_to(root_path).as_posix(),
                            "children": scan_directory(item)
                        }
                    else:
                        node = {
                            "id": f"file_{uuid.uuid4().hex[:8]}",
                            "path": item.relative_to(root_path).as_posix(),
                            "name": item.name,
                            "type": "file",
                            "size": item.stat().st_size,
                            "upload_time": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                        }
                    
                    nodes.append(node)
            except PermissionError:
                pass
            
            return nodes
        
        return [
            {
                "id": "root",
                "name": "我的文件",
                "type": "folder",
                "path": '',
                "children": scan_directory(root_path)
            }
        ]
    
    def _validate_path(self, path: str) -> bool:
        """验证路径是否合法"""
        try:
            abs_path = (self.storage_root / path.lstrip('/')).resolve()
            return str(abs_path).startswith(str(self.storage_root))
        except:
            return False
    
    def _get_node_by_id(self, node_id: str, tree: List[Dict] = None) -> Optional[Dict]:
        """通过ID查找节点"""
        if tree is None:
            tree = self.metadata
        
        for node in tree:
            if node['id'] == node_id:
                return node
            if node.get('children'):
                found = self._get_node_by_id(node_id, node['children'])
                if found:
                    return found
        return None
    
    def _remove_node_by_id(self, node_id: str, tree: List[Dict] = None) -> bool:
        """从树中删除节点"""
        if tree is None:
            tree = self.metadata
        
        for i, node in enumerate(tree):
            if node['id'] == node_id:
                tree.pop(i)
                return True
            if node.get('children'):
                if self._remove_node_by_id(node_id, node['children']):
                    return True
        return False
    
    def _flatten_tree(self, tree: List[Dict] = None) -> List[Dict]:
        """平铺树结构为列表"""
        if tree is None:
            tree = self.metadata
        
        result = []
        for node in tree:
            result.append(node)
            if node.get('children'):
                result.extend(self._flatten_tree(node['children']))
        return result
    
    def _generate_path(self, parent_path: str, name: str) -> str:
        """生成完整路径"""
        return f"{parent_path.rstrip('/')}/{secure_filename(name)}"
    
    def list_files(self) -> List[Dict]:
        """获取文件列表 - 服务逻辑"""
        with self.lock:
            return self.file_manager._flatten_tree()
    
    def create_folder(self, parent_id: str, folder_name: str) -> Dict:
        """创建文件夹 - 服务逻辑"""
        with self.lock:
            # 1. 服务层权限验证
            if not folder_name or not folder_name.strip():
                raise ValueError("文件夹名不能为空")
            
            folder_name = folder_name.strip()
            
            # 2. 调用算法层
            try:
                result = self.file_manager.create_folder(parent_id, folder_name)
                return result
            except ValueError as e:
                # 算法层的异常直接传递
                raise
            except Exception as e:
                # 算法层的其他异常包装
                raise ValueError(f"创建文件夹失败: {e}")
    
    def delete_node(self, node_id: str) -> bool:
        """删除文件或文件夹 - 服务逻辑"""
        with self.lock:
            # 1. 服务层验证
            if not node_id:
                raise ValueError("节点ID不能为空")
            
            # 2. 调用算法层
            try:
                result = self.file_manager.delete_node(node_id)
                return result
            except ValueError as e:
                # 算法层的异常直接传递
                raise
            except Exception as e:
                # 算法层的其他异常包装
                raise ValueError(f"删除节点失败: {e}")
    
    def _delete_from_knowledge_base(self, node: Dict):
        """从知识库删除相关内容"""
        from app.core.kb_manager import get_kb_manager
        
        kb_delete_success = True
        kb_manager = get_kb_manager(self.user_id)
        
        if node['type'] == 'folder':
            # 递归查找文件夹中的所有PDF文件
            all_files = self._flatten_tree([node])
            pdf_files = [f for f in all_files if f['type'] == 'file' and f['name'].lower().endswith('.pdf')]
            
            # 删除所有PDF文件的知识库内容
            for pdf_file in pdf_files:
                success = kb_manager.delete_paper(pdf_file['id'])
                if not success:
                    kb_delete_success = False
        elif node['type'] == 'file' and node['name'].lower().endswith('.pdf'):
            # 单个PDF文件
            kb_delete_success = kb_manager.delete_paper(node['id'])
        
        if not kb_delete_success:
            print(f"⚠️ 知识库内容删除部分失败，但继续删除文件: {node['id']}")
    
    def rename_node(self, node_id: str, new_name: str) -> Dict:
        """重命名文件/文件夹"""
        node = self._get_node_by_id(node_id)
        if not node:
            raise ValueError("节点不存在")
        
        if not self._validate_path(node['path']):
            raise ValueError("非法路径")
        
        # 计算旧路径和新路径
        old_path = self.storage_root / node['path'].lstrip('/')
        parent_dir = old_path.parent
        new_path = parent_dir / secure_filename(new_name)
        
        # 重命名物理文件
        if old_path.exists():
            old_path.rename(new_path)
        
        # 更新元数据
        node['name'] = new_name
        node['path'] = self._generate_path(node['path'].rsplit('/', 1)[0], new_name)
        
        # 如果是文件夹，递归更新子节点路径
        if node['type'] == 'folder':
            self._update_child_paths(node)
        
        self._save_metadata()
        return node
    
    def _update_child_paths(self, folder_node: Dict):
        """递归更新文件夹子节点的路径"""
        if not folder_node.get('children'):
            return
        
        for child in folder_node['children']:
            child['path'] = self._generate_path(folder_node['path'], child['name'])
            if child['type'] == 'folder' and child.get('children'):
                self._update_child_paths(child)


    def upload_file(self, parent_path: str, file) -> Dict:
        """上传文件 - 服务逻辑"""
        with self.lock:
            # 1. 服务层验证
            if not file or not file.filename:
                raise ValueError("无效的文件")
            
            # 2. 调用算法层
            try:
                result = self.file_manager.upload_file(parent_path, file)
                return result
            except ValueError as e:
                # 算法层的异常直接传递
                raise
            except Exception as e:
                # 算法层的其他异常包装
                raise ValueError(f"上传文件失败: {e}")
    
    async def async_upload_file(self, parent_path: str, file) -> Dict:
        """异步上传文件 - 服务逻辑"""
        # 对于异步上传，可以在这里添加额外的服务层逻辑
        # 目前直接调用同步方法
        return self.upload_file(parent_path, file)
    
    def get_file_content(self, node_id: str):
        """获取文件内容 - 服务逻辑"""
        with self.lock:
            # 1. 服务层验证
            if not node_id:
                raise ValueError("节点ID不能为空")
            
            # 2. 调用算法层
            try:
                result = self.file_manager.get_file_content(node_id)
                return result
            except ValueError as e:
                # 算法层的异常直接传递
                raise
            except Exception as e:
                # 算法层的其他异常包装
                raise ValueError(f"获取文件内容失败: {e}")
    
    # ==================== 知识库管理方法 ====================
    
    def create_knowledge_base(self, name: str, description: str = "") -> Dict:
        """创建知识库（本质是创建文件夹）"""
        import pdb; pdb.set_trace()
        with self.lock:
            # 生成知识库ID
            kb_id = str(uuid.uuid4())
            
            # 创建文件夹
            # 为了支持中文，使用UUID作为文件夹名，显示名用原始名称
            folder_name = f"kb_{kb_id}"
            
            # 创建文件夹节点
            folder_node = self.create_folder('root', folder_name)
            
            # 加载现有知识库元数据
            kb_metadata = self._load_knowledge_bases()
            
            # 添加新知识库
            new_kb = {
                "id": kb_id,
                "name": name,
                "description": description,
                "folder_id": folder_node['id'],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "file_count": 0,
                "status": "active"
            }
            
            kb_metadata["knowledge_bases"].append(new_kb)
            
            # 保存元数据
            self._save_knowledge_bases(kb_metadata)
            
            return new_kb
    
    def list_knowledge_bases(self) -> List[Dict]:
        """列出所有知识库"""
        kb_metadata = self._load_knowledge_bases()
        
        # 更新每个知识库的文件数量
        for kb in kb_metadata["knowledge_bases"]:
            try:
                folder_node = self._get_node_by_id(kb["folder_id"])
                if folder_node and folder_node["type"] == "folder":
                    kb["file_count"] = self._count_files_in_folder(folder_node)
                    kb["updated_at"] = folder_node.get("modified_at", kb["created_at"])
            except Exception:
                kb["file_count"] = 0
        
        return kb_metadata["knowledge_bases"]
    
    def get_knowledge_base_files(self, kb_id: str) -> List[Dict]:
        """获取知识库下的文件列表"""
        kb_metadata = self._load_knowledge_bases()
        
        # 找到知识库
        kb = None
        for kb_item in kb_metadata["knowledge_bases"]:
            if kb_item["id"] == kb_id:
                kb = kb_item
                break
        
        if not kb:
            raise ValueError("知识库不存在")
        
        # 获取文件夹节点
        folder_node = self._get_node_by_id(kb["folder_id"])
        if not folder_node:
            raise ValueError("知识库文件夹不存在")
        
        # 返回文件夹下的所有文件（递归）
        return self._get_all_files_in_folder(folder_node)
    
    def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库（删除文件夹及其内容）"""
        with self.lock:
            kb_metadata = self._load_knowledge_bases()
            
            # 找到知识库
            kb_index = None
            for i, kb_item in enumerate(kb_metadata["knowledge_bases"]):
                if kb_item["id"] == kb_id:
                    kb_index = i
                    break
            
            if kb_index is None:
                raise ValueError("知识库不存在")
            
            kb = kb_metadata["knowledge_bases"][kb_index]
            
            # 删除文件夹
            try:
                self.delete_node(kb["folder_id"])
            except Exception as e:
                print(f"删除文件夹失败: {e}")
            
            # 从元数据中移除知识库
            kb_metadata["knowledge_bases"].pop(kb_index)
            self._save_knowledge_bases(kb_metadata)
            
            return True
    
    def upload_to_knowledge_base(self, kb_id: str, file) -> Dict:
        """上传文件到知识库"""
        kb_metadata = self._load_knowledge_bases()
        
        # 找到知识库
        kb = None
        for kb_item in kb_metadata["knowledge_bases"]:
            if kb_item["id"] == kb_id:
                kb = kb_item
                break
        
        if not kb:
            raise ValueError("知识库不存在")
        
        # 获取文件夹节点
        folder_node = self._get_node_by_id(kb["folder_id"])
        if not folder_node:
            raise ValueError("知识库文件夹不存在")
        
        # 上传文件到文件夹
        file_node = self.upload_file(folder_node["path"], file)
        
        # 更新知识库的更新时间
        kb["updated_at"] = datetime.now().isoformat()
        kb_metadata["knowledge_bases"] = [
            kb_item if kb_item["id"] != kb_id else kb
            for kb_item in kb_metadata["knowledge_bases"]
        ]
        self._save_knowledge_bases(kb_metadata)
        
        return file_node
    
    def _load_knowledge_bases(self) -> Dict:
        """加载知识库元数据"""
        kb_metadata_path = self.storage_root / '.knowledge_bases.json'
        
        if kb_metadata_path.exists():
            try:
                with open(kb_metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载知识库元数据失败: {e}")
        
        # 返回默认结构
        return {"knowledge_bases": []}
    
    def _save_knowledge_bases(self, kb_metadata: Dict):
        """保存知识库元数据"""
        kb_metadata_path = self.storage_root / '.knowledge_bases.json'
        
        try:
            with open(kb_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(kb_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存知识库元数据失败: {e}")
    
    def _count_files_in_folder(self, folder_node: Dict) -> int:
        """统计文件夹中的文件数量（递归）"""
        count = 0
        if folder_node.get("children"):
            for child in folder_node["children"]:
                if child["type"] == "file":
                    count += 1
                elif child["type"] == "folder":
                    count += self._count_files_in_folder(child)
        return count
    
    def _get_all_files_in_folder(self, folder_node: Dict) -> List[Dict]:
        """获取文件夹中的所有文件（递归）"""
        files = []
        if folder_node.get("children"):
            for child in folder_node["children"]:
                if child["type"] == "file":
                    files.append(child)
                elif child["type"] == "folder":
                    files.extend(self._get_all_files_in_folder(child))
        return files


# 延迟初始化全局服务实例（保持兼容性）
file_service = None

def get_file_service(user_id: str = None):
    """获取文件服务实例（延迟初始化）"""
    global file_service
    if file_service is None:
        file_service = FileService(user_id)
    return file_service

def get_user_file_service():
    """获取当前用户的文件服务实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return FileService(user_id)
