"""
文件管理核心类 - 负责文件系统操作和元数据管理
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


class FileManager:
    """文件管理核心类 - 负责文件系统操作和元数据管理"""
    
    def __init__(self, storage_root: Path, metadata_path: Path):
        """
        初始化文件管理器
        
        Args:
            storage_root: 文件存储根目录
            metadata_path: 元数据文件路径
        """
        self.storage_root = storage_root
        self.metadata_path = metadata_path
        
        # 确保存储目录存在
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        # 并发锁
        self.lock = Lock()
        
        # 初始化或加载元数据
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> List[Dict]:
        """加载文件树元数据"""
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载元数据失败: {e}")
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
                            "size": 0,
                            "created_at": datetime.fromtimestamp(item.stat().st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                            "children": scan_directory(item)
                        }
                    else:
                        file_stat = item.stat()
                        node = {
                            "id": f"file_{uuid.uuid4().hex[:8]}",
                            "path": item.relative_to(root_path).as_posix(),
                            "name": item.name,
                            "type": "file",
                            "size": file_stat.st_size,
                            "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                            "upload_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                            "file_type": item.suffix.lower(),
                            "parent_id": None  # 将在后续处理中设置
                        }
                    
                    nodes.append(node)
            except PermissionError as e:
                print(f"权限错误，跳过目录 {current_path}: {e}")
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
        """验证路径是否合法（防止路径遍历攻击）"""
        try:
            abs_path = (self.storage_root / path.lstrip('/')).resolve()
            return str(abs_path).startswith(str(self.storage_root))
        except Exception:
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
    
    def _update_child_paths(self, folder_node: Dict):
        """递归更新文件夹子节点的路径"""
        if not folder_node.get('children'):
            return
        
        for child in folder_node['children']:
            child['path'] = self._generate_path(folder_node['path'], child['name'])
            if child['type'] == 'folder' and child.get('children'):
                self._update_child_paths(child)
    
    def _find_parent_node(self, child_path: str) -> Optional[Dict]:
        """根据子节点路径查找父节点"""
        # 从路径中提取父路径
        parent_path = str(Path(child_path).parent)
        
        # 查找匹配的父节点
        all_nodes = self._flatten_tree()
        for node in all_nodes:
            if node['path'] == parent_path:
                return node
        return None
    
    # ==================== 公共接口 ====================
    
    def list_files(self) -> List[Dict]:
        """获取文件树列表"""
        return self.metadata
    
    def create_folder(self, parent_id: str, folder_name: str) -> Dict:
        """新建文件夹"""
        parent_node = self._get_node_by_id(parent_id)
        if not parent_node:
            raise ValueError("父节点不存在")
        
        parent_path = parent_node['path']
        
        if not self._validate_path(parent_path):
            raise ValueError("非法路径")
        
        # 生成安全路径
        new_path = self._generate_path(parent_path, folder_name)
        
        # 创建物理目录
        physical_path = self.storage_root / new_path.lstrip('/')
        physical_path.mkdir(parents=True, exist_ok=True)
        
        # 生成新节点
        current_time = datetime.now().isoformat()
        new_node = {
            "id": f"folder_{uuid.uuid4().hex[:8]}",
            "name": folder_name,
            "type": "folder",
            "path": new_path,
            "size": 0,
            "created_at": current_time,
            "modified_at": current_time,
            "parent_id": parent_id,
            "children": []
        }
        
        # 添加到元数据
        parent_node.setdefault('children', []).append(new_node)
        self._save_metadata()
        
        return new_node
    
    def delete_node(self, node_id: str) -> bool:
        """删除文件或文件夹"""
        node = self._get_node_by_id(node_id)
        if not node:
            raise ValueError("节点不存在")
        
        # 验证删除操作
        validation = self.validate_node_operation(node_id, "delete")
        if not validation["valid"]:
            raise ValueError(validation["reason"])
        
        if not self._validate_path(node['path']):
            raise ValueError("非法路径")
        
        physical_path = self.storage_root / node['path'].lstrip('/')
        
        # 删除物理文件/文件夹
        if physical_path.exists():
            try:
                if node['type'] == 'folder':
                    shutil.rmtree(physical_path)
                else:
                    physical_path.unlink()
            except OSError as e:
                raise ValueError(f"删除物理文件失败: {e}")
        
        # 从元数据删除
        result = self._remove_node_by_id(node_id)
        if result:
            self._save_metadata()
        
        return result
    
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
    
    def upload_file(self, parent_path: str, file) -> Dict:
        """上传文件"""
        if not self._validate_path(parent_path):
            raise ValueError("非法路径")
        
        # 保存文件
        filename = secure_filename(file.filename)
        save_dir = self.storage_root / parent_path.lstrip('/')
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = file_path
        while file_path.exists():
            name, ext = os.path.splitext(str(original_path))
            file_path = Path(f"{name}_{counter}{ext}")
            counter += 1
        
        # 保存文件内容
        file.save(str(file_path))
        file_size = file_path.stat().st_size
        
        # 获取父节点
        parent_node = self.get_node_by_path(parent_path)
        if not parent_node:
            raise ValueError("父路径不存在")
        
        # 使用算法层创建文件节点
        file_node = self.create_file_node(
            parent_id=parent_node['id'],
            file_name=file_path.name,
            file_size=file_size,
            file_type=file_path.suffix
        )
        
        # 设置文件路径
        file_node['path'] = f"{parent_path}/{file_path.name}".lstrip('/')
        
        # 添加到父节点
        parent_node.setdefault('children', []).append(file_node)
        
        # 保存元数据
        self._save_metadata()
        
        return file_node
    
    def get_file_content(self, node_id: str) -> Path:
        """获取文件内容（用于预览）"""
        node = self._get_node_by_id(node_id)
        if not node or node['type'] != 'file':
            raise ValueError("文件不存在")
        
        physical_path = self.storage_root / node['path'].lstrip('/')
        if not physical_path.exists():
            raise FileNotFoundError("文件不存在")
        
        return physical_path
    
    def get_node_by_path(self, path: str) -> Optional[Dict]:
        """根据路径获取节点"""
        all_nodes = self._flatten_tree()
        for node in all_nodes:
            if node['path'] == path:
                return node
        return None
    
    def refresh_metadata(self):
        """刷新元数据（从文件系统重新扫描）"""
        self.metadata = self._build_file_tree()
        self._save_metadata()
    
    def get_storage_stats(self) -> Dict:
        """获取存储统计信息"""
        all_files = self._flatten_tree()
        file_nodes = [node for node in all_files if node['type'] == 'file']
        
        total_size = sum(node['size'] for node in file_nodes)
        total_files = len(file_nodes)
        total_folders = len([node for node in all_files if node['type'] == 'folder'])
        
        return {
            'total_size': total_size,
            'total_files': total_files,
            'total_folders': total_folders,
            'storage_path': str(self.storage_root)
        }
    
    # === 知识库相关算法 ===
    def count_files_in_folder(self, folder_node: Dict) -> int:
        """统计文件夹中的文件数量（递归）"""
        count = 0
        if folder_node.get("children"):
            for child in folder_node["children"]:
                if child["type"] == "file":
                    count += 1
                elif child["type"] == "folder":
                    count += self.count_files_in_folder(child)
        return count
    
    def get_all_files_in_folder(self, folder_node: Dict) -> List[Dict]:
        """获取文件夹中的所有文件（递归）"""
        files = []
        if folder_node.get("children"):
            for child in folder_node["children"]:
                if child["type"] == "file":
                    files.append(child)
                elif child["type"] == "folder":
                    files.extend(self.get_all_files_in_folder(child))
        return files
    
    def filter_files_by_type(self, files: List[Dict], file_types: List[str]) -> List[Dict]:
        """按类型过滤文件"""
        if not file_types:
            return files
        
        # 标准化文件类型（统一为小写，添加点号前缀）
        normalized_types = []
        for ft in file_types:
            ft = ft.lower().strip()
            if not ft.startswith('.'):
                ft = '.' + ft
            normalized_types.append(ft)
        
        filtered_files = []
        for file in files:
            file_ext = Path(file['name']).suffix.lower()
            if file_ext in normalized_types:
                filtered_files.append(file)
        
        return filtered_files
    
    def calculate_folder_size(self, folder_node: Dict) -> int:
        """计算文件夹总大小（递归）"""
        total_size = 0
        if folder_node.get("children"):
            for child in folder_node["children"]:
                if child["type"] == "file":
                    total_size += child.get("size", 0)
                elif child["type"] == "folder":
                    total_size += self.calculate_folder_size(child)
        return total_size
    
    def find_nodes_by_name(self, tree: List[Dict], name: str, exact_match: bool = False) -> List[Dict]:
        """根据名称查找节点"""
        results = []
        name = name.lower()
        
        def search_recursive(nodes):
            for node in nodes:
                node_name = node['name'].lower()
                
                if exact_match:
                    if node_name == name:
                        results.append(node)
                else:
                    if name in node_name:
                        results.append(node)
                
                # 递归搜索子节点
                if node.get("children"):
                    search_recursive(node["children"])
        
        search_recursive(tree)
        return results
    
    def get_node_path(self, node_id: str, tree: List[Dict] = None) -> Optional[str]:
        """获取节点的完整路径"""
        if tree is None:
            tree = self._load_metadata()
        
        def find_path_recursive(nodes, target_id, current_path=""):
            for node in nodes:
                # 构建当前节点的路径
                node_path = f"{current_path}/{node['name']}" if current_path else node['name']
                
                if node['id'] == target_id:
                    return node_path
                
                # 递归搜索子节点
                if node.get("children"):
                    result = find_path_recursive(node["children"], target_id, node_path)
                    if result:
                        return result
            
            return None
        
        return find_path_recursive(tree, node_id)
    
    def validate_node_operation(self, node_id: str, operation: str, tree: List[Dict] = None) -> Dict:
        """验证节点操作的合法性"""
        if tree is None:
            tree = self._load_metadata()
        
        node = self._get_node_by_id(node_id, tree)
        if not node:
            return {"valid": False, "reason": "节点不存在"}
        
        # 根据操作类型验证
        if operation == "delete":
            if node.get("type") == "folder" and node.get("children"):
                # 检查是否有正在使用的文件
                files = self.get_all_files_in_folder(node)
                if files:
                    return {"valid": False, "reason": f"文件夹包含 {len(files)} 个文件，请先删除文件"}
        
        elif operation == "rename":
            # 检查名称是否已存在于同级
            parent_id = node.get("parent_id")
            if parent_id:
                parent = self._get_node_by_id(parent_id, tree)
                if parent and parent.get("children"):
                    existing_names = [child["name"] for child in parent["children"] if child["id"] != node_id]
                    # 这里可以在调用时检查新名称是否重复
        
        return {"valid": True}
    
    def create_file_node(self, parent_id: str, file_name: str, file_size: int, file_type: str = "") -> Dict:
        """创建文件节点的算法逻辑"""
        new_node = {
            "id": str(uuid.uuid4()),
            "name": file_name,
            "type": "file",
            "size": file_size,
            "parent_id": parent_id,
            "created_at": str(Path(file_name).suffix),
            "modified_at": datetime.now().isoformat(),
            "file_type": file_type or Path(file_name).suffix
        }
        return new_node
    
    def batch_delete_nodes(self, node_ids: List[str], tree: List[Dict] = None) -> Dict:
        """批量删除节点"""
        if tree is None:
            tree = self._load_metadata()
        
        results = {
            "success": [],
            "failed": [],
            "total_deleted": 0
        }
        
        for node_id in node_ids:
            try:
                validation = self.validate_node_operation(node_id, "delete", tree)
                if not validation["valid"]:
                    results["failed"].append({
                        "node_id": node_id,
                        "reason": validation["reason"]
                    })
                    continue
                
                if self._remove_node_by_id(node_id, tree):
                    results["success"].append(node_id)
                    results["total_deleted"] += 1
                else:
                    results["failed"].append({
                        "node_id": node_id,
                        "reason": "删除失败"
                    })
            except Exception as e:
                results["failed"].append({
                    "node_id": node_id,
                    "reason": str(e)
                })
        
        return results
    
    def export_tree_structure(self, tree: List[Dict] = None, format: str = "json") -> str:
        """导出文件树结构"""
        if tree is None:
            tree = self._load_metadata()
        
        if format == "json":
            return json.dumps(tree, ensure_ascii=False, indent=2)
        
        elif format == "text":
            def tree_to_text(nodes, indent=0):
                text = ""
                for node in nodes:
                    prefix = "  " * indent + ("📁 " if node["type"] == "folder" else "📄 ")
                    text += prefix + node["name"] + "\n"
                    
                    if node.get("children"):
                        text += tree_to_text(node["children"], indent + 1)
                
                return text
            
            return tree_to_text(tree)
        
        else:
            raise ValueError(f"不支持的导出格式: {format}")