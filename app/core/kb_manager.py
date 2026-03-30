"""
知识库管理核心模块 - 从原knowledge_base_manager.py迁移并重构
去除Flask依赖，保持纯算法逻辑
支持ChromaDB和Qdrant双引擎
"""

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import uuid
import json
import torch
import os

from app.config import Config
from app.extensions import get_chroma_client, get_embedder, get_qdrant_client

from app.models.schemas import PaperMetadata

# Qdrant相关导入
try:
    from qdrant_client.models import (
        Distance, 
        VectorParams, 
        PointStruct, 
        Filter, 
        FieldCondition, 
        MatchValue, 
        MatchText, 
        Range,
        ScoredPoint,
        QueryResponse
        )
    from qdrant_client.http.models import CollectionInfo
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("⚠️ Qdrant客户端未安装，将使用ChromaDB")


class KnowledgeBaseManager:
    """向量数据库管理器 - 支持ChromaDB和Qdrant"""
    _instances = {}  # 存储不同参数的实例 {key: instance}
    
    def __new__(cls, 
                persist_directory=None, 
                device: Optional[str] = 'cpu', 
                user_id: str = None):
        """
        基于参数的单例模式实现
        对于Qdrant，所有用户共享同一个实例
        """
        # 使用固定的向量数据库路径
        if persist_directory is None:
            persist_directory = Config.QDRANT_STORAGE_PATH if Config.USE_QDRANT and QDRANT_AVAILABLE else Config.VECTOR_DB_PATH
            
        # 创建实例的唯一键
        device_key = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # 根据配置决定使用哪个数据库引擎
        db_engine = "qdrant" if Config.USE_QDRANT and QDRANT_AVAILABLE else "chromadb"
        
        # 对于Qdrant，所有用户共享同一个实例，忽略user_id参数
        if Config.USE_QDRANT and QDRANT_AVAILABLE:
            instance_key = f"qdrant_shared_instance"
        else:
            # ChromaDB仍按用户分离
            instance_key = f"{persist_directory}_{device_key}_{db_engine}_{user_id}"
        
        # 如果该参数组合的实例不存在，创建新实例
        if instance_key not in cls._instances:
            cls._instances[instance_key] = super(KnowledgeBaseManager, cls).__new__(cls)
            cls._instances[instance_key]._initialized = False
        
        return cls._instances[instance_key]
    
    def __init__(self, persist_directory=None, device: Optional[str] = None, user_id: str = None):
        """
        初始化向量数据库管理器
        """
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # 使用配置的默认值（固定向量数据库路径）
        if persist_directory is None:
            persist_directory = Config.VECTOR_DB_PATH  # 使用固定路径
            
        # 确保目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        # 1. 确定使用的数据库引擎
        self.use_qdrant = Config.USE_QDRANT and QDRANT_AVAILABLE
        # 对于Qdrant，user_id在运行时动态获取，不存储在实例中
        # self._user_id = user_id if not self.use_qdrant else None
        self._user_id = user_id
        
        if self.use_qdrant:
            print(f"💽 初始化Qdrant向量数据库（统一集合）")
            self._init_qdrant()
        else:
            print(f"💽 初始化ChromaDB向量数据库，用户: {user_id or 'global'}")
            self._init_chromadb()
        
        # 2. 确定运行设备
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"⚙️  Embedding 计算设备: {device.upper()}")
        
        # 3. 获取 Embedding 模型
        try:
            self.embedder = get_embedder()
            if self.embedder is None:
                raise Exception("Embedding模型未初始化")
        except:
            # 如果扩展未初始化，直接创建模型
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        
        # 4. 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2048,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        # 5. 保存实例参数
        self.persist_directory = persist_directory
        self.device = device
        
        # 标记为已初始化
        self._initialized = True
    
    
    def _init_qdrant(self):
        """初始化Qdrant"""
        try:
            self.client = get_qdrant_client()
            if self.client is None:
                raise Exception("Qdrant客户端未初始化")
        except Exception as e:
            print(f"❌ 获取Qdrant客户端失败: {e}")
            raise
        
        # 使用统一的集合名称
        self.collection_name = Config.get_collection_name()
        
        # 确保集合存在（只初始化一次）
        if not hasattr(self, '_collection_ensured') or not self._collection_ensured:
            self._ensure_qdrant_collection_exists()
            self._collection_ensured = True
    
    def _init_chromadb(self):
        """初始化ChromaDB"""
        try:
            self.client = get_chroma_client(user_id=self._user_id)
            if self.client is None:
                raise Exception("ChromaDB客户端未初始化")
        except Exception as e:
            print(f"❌ 获取ChromaDB客户端失败: {e}")
            raise
        
        # 使用用户专属的集合名称
        self.collection_name = f"papers_{self._user_id or 'default'}"
        
        # 确保集合存在
        try:
            self.client.get_collection(self.collection_name)
        except:
            self.client.create_collection(self.collection_name)
            print(f"✅ 创建ChromaDB集合: {self.collection_name}")
    
    @property
    def user_id(self):
        """动态获取当前用户ID"""
        return self._user_id
        if self.use_qdrant:
            # Qdrant模式下动态获取用户ID
            from app.core.user_context import UserContext
            return UserContext.get_current_user_id()
        else:
            # ChromaDB模式下使用存储的用户ID
            return self._user_id
    
    def _ensure_qdrant_collection_exists(self):
        """确保Qdrant集合存在"""
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == self.collection_name for col in collections)
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=Config.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ 创建Qdrant集合: {self.collection_name}")
        except Exception as e:
            print(f"❌ 创建Qdrant集合失败: {e}")
            raise
    
    @classmethod
    def reset_instance(cls, persist_directory=None, device: Optional[str] = None):
        """重置特定参数的单例实例"""
        if persist_directory is None:
            persist_directory = Config.VECTOR_DB_PATH
            
        device_key = device or ("cuda" if torch.cuda.is_available() else "cpu")
        instance_key = f"{persist_directory}_{device_key}"
        
        if instance_key in cls._instances:
            del cls._instances[instance_key]
    
    @classmethod
    def reset_all_instances(cls):
        """重置所有实例"""
        cls._instances.clear()

    def _flatten_metadata(self, metadata_obj: PaperMetadata, file_id: str = None) -> Dict[str, Any]:
        """
        将 PaperMetadata 对象转换为扁平字典（直接使用 model_dump）
        """
        # 将 Pydantic 对象转为 dict
        data = metadata_obj.model_dump()
    
        # 设置 paper_id
        data['paper_id'] = file_id if file_id else data.get('id', str(uuid.uuid4()))
    
        # 确保年份是整数
        if not isinstance(data['year'], int):
            try:
                import re
                year_str = str(data['year'])
                year_match = re.search(r'\d{4}', year_str)
                data['year'] = int(year_match.group()) if year_match else 0
            except Exception:
                data['year'] = 0
    
        # 确保引用次数有默认值
        if not data.get('citation_count') or data['citation_count'] == "":
            data['citation_count'] = "N/A"
    
        # 确保 has_code 正确
        data['has_code'] = bool(data.get('code_url'))
    
        return data
    

    def add_paper(self, full_text: str, metadata_obj, file_id: str = None, kb_id: str = None):
        """
        将论文存入向量数据库（添加摘要和原文）
        Args:
            full_text: 论文全文
            metadata_obj: 论文元数据对象
            file_id: 文件ID
            kb_id: 知识库ID
        Returns:
            {'summary_id': ..., 'chunk_count': ...}
        """
        if self.use_qdrant:
            # 1. 先添加摘要
            summary_id = self._add_paper_summary_qdrant(metadata_obj, file_id, kb_id)
            
            # 2. 再添加原文
            chunk_count = self._add_paper_fulltext_qdrant(full_text, file_id, kb_id)
            
            return {'summary_id': summary_id, 'chunk_count': chunk_count}


    def _add_paper_summary_qdrant(self, metadata_obj, file_id: str = None, kb_id: str = None):
        """添加论文摘要到Qdrant
        Args:
            metadata_obj: 论文元数据对象（包含 title, authors, year, summary 等信息）
            file_id: 文件ID
            kb_id: 知识库ID
        Returns:
            summary_point_id: 摘要点ID
        """
        # 动态获取当前用户ID
        current_user_id = self.user_id
        
        # 1. 准备元数据
        flat_metadata = self._flatten_metadata(metadata_obj, file_id)
        paper_id = flat_metadata['paper_id']
        paper_title = flat_metadata['title']
        
        print(f"📥 正在添加摘要到Qdrant: {paper_title} (ID: {paper_id}, 用户: {current_user_id}, KB: {kb_id})")
        
        # 2. 构建摘要内容
        try:
            summary_text = self._build_summary_text(metadata_obj)
        except:
            summary_text = f"Title: {metadata_obj.title}\nAbstract: {metadata_obj.abstract}"
        summary_embedding = self.embedder.encode(summary_text).tolist()
        
        # 3. 生成摘要点ID
        summary_point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, paper_id))
        
        # 4. 添加论文摘要点
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=summary_point_id,
                    vector=summary_embedding,
                    payload={
                        "type": "summary",
                        "content": summary_text,
                        "metainfo": flat_metadata,  # 整个元数据对象
                        "user_id": current_user_id,
                        "file_id": paper_id,
                        "kb_id": kb_id
                    }
                )
            ]
        )
        
        print(f"   ✅ 摘要添加完成 (ID: {summary_point_id})")
        return summary_point_id


    def _add_paper_fulltext_qdrant(self, full_text: str, file_id: str, kb_id: str = None, elements: List = None):
        """添加论文原文（分块）到Qdrant
        支持智能分段和增强元数据
        
        Args:
            full_text: 论文全文
            file_id: 文件ID
            kb_id: 知识库ID
            elements: unstructured 结构化元素列表（可选，用于智能分段和增强元数据）
            
        Returns:
            chunk_count: 添加的chunk数量
        """
        # 动态获取当前用户ID
        current_user_id = self.user_id
        
        print(f"📥 正在添加原文到Qdrant (ID: {file_id}, 用户: {current_user_id}, KB: {kb_id})")
        
        # ✅ 优化：如果提供了 elements，使用 unstructured 的智能分段
        if elements is not None:
            print(f"   🧠 使用 unstructured 智能分段模式")
            chunks = []
            chunk_metadata = []  # 存储每个 chunk 的元数据
            
            for element in elements:
                if element.category in ["Title", "NarrativeText", "ListItem"]:
                    # 文本类元素
                    chunks.append(element.text)
                    chunk_metadata.append({
                        "category": element.category,
                        "page_number": element.metadata.page_number if hasattr(element.metadata, 'page_number') else None,
                        "parent_id": element.metadata.parent_id if hasattr(element.metadata, 'parent_id') else None,
                    })
                elif element.category == "Table":
                    # 表格：转换为 HTML 格式
                    table_html = element.metadata.text_as_html if hasattr(element.metadata, 'text_as_html') else element.text
                    chunks.append(table_html)
                    chunk_metadata.append({
                        "category": "Table",
                        "page_number": element.metadata.page_number if hasattr(element.metadata, 'page_number') else None,
                        "table_cells_count": len(element.metadata.table_cells) if hasattr(element.metadata, 'table_cells') else 0,
                    })
                elif element.category == "Image":
                    # 图片：添加标题和上下文
                    caption = element.metadata.caption if hasattr(element.metadata, 'caption') else ""
                    image_text = f"[Image: {caption}]" if caption else "[Image]"
                    chunks.append(image_text)
                    chunk_metadata.append({
                        "category": "Image",
                        "page_number": element.metadata.page_number if hasattr(element.metadata, 'page_number') else None,
                        "image_path": element.metadata.image_path if hasattr(element.metadata, 'image_path') else None,
                        "caption": caption,
                    })
            
            print(f"   📊 智能分段统计: {len(chunks)} 个片段")
        else:
            # ✅ 兼容：如果没有提供 elements，使用原有的机械切分
            print(f"   🔪 使用传统机械分段模式")
            chunks = self.text_splitter.split_text(full_text)
            chunk_metadata = [{}] * len(chunks)  # 空元数据
        
        if chunks:
            print(f"   🔪 全文切分为 {len(chunks)} 个片段...")
            
            chunk_embeddings = self.embedder.encode(chunks).tolist()
            chunk_points = []
            
            for idx, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                chunk_id = f"{file_id}_chunk_{idx}"
                chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

                # ✅ 增强元数据
                chunk_payload = {
                    "type": "chunk",
                    "content": chunk,
                    "paper_id": file_id,
                    "chunk_index": idx,
                    "user_id": current_user_id,
                    "file_id": file_id,
                    "kb_id": kb_id,
                    # ✅ 新增：增强元数据
                    "chunk_metadata": chunk_metadata[idx] if idx < len(chunk_metadata) else {},
                }
                
                chunk_points.append(PointStruct(id=chunk_id, vector=embedding, payload=chunk_payload))
            
            # 批量添加chunks
            self.client.upsert(
                collection_name=self.collection_name,
                points=chunk_points
            )
        
        print(f"   ✅ 原文添加完成 (共 {len(chunks)} 个片段)")
        return len(chunks)
    
    
    def _build_summary_text(self, metadata: PaperMetadata) -> str:
        """构建摘要文本"""
        return (
            f"Title: {metadata.title}\n"
            f"Year: {metadata.year}\n"
            f"Venue: {metadata.venue}\n"
            f"Task: {metadata.tasks}\n"
            f"Method Framework: {metadata.methods}\n"
            f"Problem: {metadata.problem}\n"
            f"Core Contribution: {metadata.contribution}\n"
            f"Key Metrics: {metadata.metrics}\n"
            f"Abstract: {metadata.abstract}"
        )
    def delete_paper(self, file_id: str, kb_id: str = None) -> bool:
        """
        根据文件ID删除知识库中的论文内容和元数据
        Args:
            file_id: 文件ID
            kb_id: 知识库ID（可选，如果指定则只删除该知识库中的数据）
        """
        if self.use_qdrant:
            return self._delete_paper_qdrant(file_id, kb_id)


    def _delete_paper_qdrant(self, file_id: str, kb_id: str = None) -> bool:
        """使用Qdrant删除论文
        Args:
            file_id: 文件ID
            kb_id: 知识库ID（可选，如果指定则只删除该知识库中的数据）
        """
        try:
            print(f"🗑️ 正在从Qdrant删除论文: {file_id} (KB: {kb_id})")

            # 构建过滤条件
            must_conditions = [FieldCondition(key="file_id", match=MatchValue(value=file_id))]
            if kb_id:
                must_conditions.append(FieldCondition(key="kb_id", match=MatchValue(value=kb_id)))

            # 删除所有匹配的点（包括摘要和chunks）
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=must_conditions)
            )

            print(f"✅ 已从Qdrant删除论文: {file_id}")
            return True

        except Exception as e:
            print(f"❌ 从Qdrant删除论文失败: {e}")
            return False


    def search(self, query: str, mode="hybrid", top_k=3, filters=None):
        """
        搜索接口
        """
        if self.use_qdrant:
            return self._search_qdrant(query, mode, top_k, filters)
        
    
    def _search_qdrant(self, 
                       query: str, 
                       mode="hybrid", 
                       top_k=3, 
                       filters=None) -> Dict:
        """使用Qdrant搜索"""
        # import pdb; pdb.set_trace()  # --- IGNORE ---

        query_embedding = self.embedder.encode(query).tolist()
        
        # 构建过滤器
        if not filters:
            search_filter = self._build_qdrant_search_filter(filters)
        else:
            search_filter = filters
        
        # 根据模式选择搜索策略
        if mode == "summary":
            search_filter.must.append(FieldCondition(key="type", match=MatchValue(value="summary")))
        elif mode == "detail":
            search_filter.must.append(FieldCondition(key="type", match=MatchValue(value="chunk")))
        # hybrid模式不限制类型
        
        mode_name = "论文推荐 (Summary)" if mode == "summary" else "细节检索 (Chunk)" if mode == "detail" else "混合检索 (Hybrid)"
        print(f"🔍 [Qdrant {mode_name}] Query: {query}")
        if filters:
            print(f"   Filters: {filters}")
        
        try:
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=search_filter,
                limit=top_k
            )
            
            # self.client.set_model(Config.QDRANT_EMBEDDING_MODEL)  # 设置Embedding模型

            # 转换为原有格式以保持兼容性
            return self._convert_qdrant_search_result(search_result.points)
            
        except Exception as e:
            print(f"❌ Qdrant搜索出错: {e}")
            return None
    
    
    def _build_qdrant_search_filter(self, filters=None) -> Filter:
        """构建Qdrant过滤器"""
        conditions = []
        
        # 动态获取当前用户ID
        current_user_id = self.user_id
        
        # 用户隔离过滤器
        if current_user_id:
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=current_user_id)))
        
        # 自定义过滤器 - 通过metainfo字段访问
        if filters:
            for key, value in filters.items():
                if key == "year" and isinstance(value, dict):
                    # 年份范围查询
                    if "$gte" in value or "$lte" in value:
                        range_condition = {}
                        if "$gte" in value:
                            range_condition["gte"] = value["$gte"]
                        if "$lte" in value:
                            range_condition["lte"] = value["$lte"]
                        conditions.append(
                            FieldCondition(
                                key="metainfo.year", 
                                range=Range(**range_condition)
                            )
                        )
                elif isinstance(value, str) and "$contains" in value:
                    # 文本包含查询
                    search_text = value.replace("$contains", "")
                    conditions.append(
                        FieldCondition(
                            key=f"metainfo.{key}", 
                            match=MatchText(text=search_text)
                        )
                    )
                else:
                    # 精确匹配
                    conditions.append(
                        FieldCondition(
                            key=f"metainfo.{key}", 
                            match=MatchValue(value=value)
                        )
                    )
        
        return Filter(must=conditions)
    
    def _convert_qdrant_search_result(self, search_result: List[ScoredPoint]) -> Dict[str, List]:
        """将Qdrant搜索结果转换为原有格式"""
        documents = []
        metadatas = []
        ids = []
        
        for hit in search_result:
            documents.append(hit.payload.get("content", ""))
            
            # 从metainfo字段提取元数据
            metainfo = hit.payload.get("metainfo", {})
            
            # 添加一些payload级别的字段
            if "type" in hit.payload:
                metainfo["result_type"] = hit.payload["type"]
            if "chunk_index" in hit.payload:
                metainfo["chunk_index"] = hit.payload["chunk_index"]
            
            metadatas.append(metainfo)
            ids.append(hit.id)
        
        return {
            "documents": [documents],
            "metadatas": [metadatas],
            "ids": [ids]
        }
    
    def search_by_paper_id(self, query: str, paper_id: str, top_k=5):
        """
        基于论文ID的精确检索
        """
        return self._search_by_paper_id_qdrant(query, paper_id, top_k)
    
    def search_by_file_ids(self, query: str, kb_id: str, file_ids: List[str], top_k: int = 5):
        """
        基于知识库和指定文件ID的搜索
        
        Args:
            query: 查询文本
            kb_id: 知识库ID
            file_ids: 文件ID列表
            top_k: 返回结果数量
        
        Returns:
            搜索结果字典，如果 file_ids 为空则返回 None
        """
        if not file_ids or len(file_ids) == 0:
            # 文件ID为空，返回 None（表示不使用知识库）
            return None
        
        if self.use_qdrant:
            return self._search_by_file_ids_qdrant(query, kb_id, file_ids, top_k)
        else:
            # ChromaDB暂不支持此功能
            print("⚠️ ChromaDB暂不支持基于文件ID的搜索")
            return None

    
    def _search_by_paper_id_qdrant(self, query: str, paper_id: str, top_k:int=10):
        """使用Qdrant进行论文精确检索"""
        query_embedding = self.embedder.encode(query).tolist()
        # import pdb; pdb.set_trace()  # --- IGNORE ---
        
        print(f"🎯 [Qdrant 论文精确检索] Query: {query}, Paper ID: {paper_id}")
        
        try:
            # 首先从chunks中检索该论文的相关内容
            search_filter = Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=self.user_id)),
                    FieldCondition(key="file_id", match=MatchValue(value=paper_id)),
                    FieldCondition(key="type", match=MatchValue(value="chunk")),
                ]
            )
            
            chunk_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=search_filter,
                limit=top_k
            )
            chunk_results = chunk_results.points
            
            # 如果该论文的内容不足，补充检索相关论文内容
            if len(chunk_results) < top_k:
                remaining_k = top_k - len(chunk_results)
                
                # 检索其他论文的摘要
                summary_filter = Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=self.user_id)),
                        FieldCondition(key="type", match=MatchValue(value="summary"))
                    ],
                    must_not=[
                        FieldCondition(key="file_id", match=MatchValue(value=paper_id))
                    ]
                )
                
                related_results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    query_filter=summary_filter,
                    limit=remaining_k
                )
                
                # 合并结果
                chunk_results.extend(related_results.points)
            
            return self._convert_qdrant_search_result(chunk_results[:top_k])
            
        except Exception as e:
            print(f"❌ Qdrant论文精确检索出错: {e}")
            return None
    
    def _search_by_file_ids_qdrant(self, query: str, kb_id: str, file_ids: List[str], top_k: int = 5):
        """使用Qdrant进行基于文件ID的搜索"""
        query_embedding = self.embedder.encode(query).tolist()
        
        print(f"📄 [Qdrant 文件精确检索] Query: {query}, KB ID: {kb_id}, File IDs: {file_ids}")
        
        try:
            # 构建过滤器：匹配用户ID、知识库ID和文件ID列表
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=self.user_id)),
                FieldCondition(key="kb_id", match=MatchValue(value=kb_id)),
                FieldCondition(key="type", match=MatchValue(value="chunk")),
            ]
            
            # 添加文件ID匹配（支持多个文件）
            if len(file_ids) == 1:
                must_conditions.append(FieldCondition(key="file_id", match=MatchValue(value=file_ids[0])))
            else:
                # 多个文件ID使用 should 条件（OR逻辑）
                must_conditions.append(
                    Filter(
                        should=[
                            FieldCondition(key="file_id", match=MatchValue(value=file_id)) 
                            for file_id in file_ids
                        ]
                    )
                )
            
            search_filter = Filter(must=must_conditions)
            
            # 检索相关文档片段
            chunk_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=search_filter,
                limit=top_k
            )
            
            return self._convert_qdrant_search_result(chunk_results.points)
            
        except Exception as e:
            print(f"❌ Qdrant文件精确检索出错: {e}")
            return None
    
    
    # Qdrant特有的高级搜索方法
    def advanced_search(self, query: str, filters: Dict = None, top_k: int = 5):
        """高级搜索，支持复杂的过滤条件（仅Qdrant）"""
        if not self.use_qdrant:
            print("⚠️ 高级搜索仅支持Qdrant")
            return self.search(query, mode="hybrid", top_k=top_k, filters=filters)
        
        conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=self.user_id))
        ]
        
        if filters:
            # 构建复杂过滤器
            filter_conditions = []
            
            # 年份过滤
            if "year_range" in filters:
                min_year, max_year = filters["year_range"]
                filter_conditions.append(
                    FieldCondition(
                        key="metainfo.year",
                        range=Range(gte=min_year, lte=max_year)
                    )
                )
            
            # 会议过滤（支持多个）
            if "venues" in filters:
                venue_conditions = [
                    FieldCondition(
                        key="metainfo.venue",
                        match=MatchText(text=venue)
                    ) for venue in filters["venues"]
                ]
                if venue_conditions:
                    filter_conditions.append(
                        Filter(
                            should=venue_conditions
                        )
                    )
            
            # 任务过滤（支持多个）
            if "tasks" in filters:
                task_conditions = [
                    FieldCondition(
                        key="metainfo.tasks",
                        match=MatchText(text=task)
                    ) for task in filters["tasks"]
                ]
                if task_conditions:
                    filter_conditions.append(
                        Filter(should=task_conditions)
                    )
            
            # 是否有代码
            if "has_code" in filters:
                filter_conditions.append(
                    FieldCondition(
                        key="metainfo.has_code",
                        match=MatchValue(value=filters["has_code"])
                    )
                )
            
            # 将所有条件用AND连接
            if filter_conditions:
                if len(filter_conditions) == 1:
                    conditions.extend(filter_conditions)
                else:
                    conditions.append(Filter(must=filter_conditions))
        
        search_filter = Filter(must=conditions)
        
        try:
            search_result = self._search_qdrant(
                query=query,
                mode="hybrid",
                top_k=top_k,
                filters=search_filter
            )

            
            return search_result
            
        except Exception as e:
            print(f"❌ 高级搜索失败: {e}")
            return None
    
    def get_similar_papers(self, paper_id: str, top_k: int = 5):
        """获取相似论文（仅Qdrant）"""
        if not self.use_qdrant:
            print("⚠️ 相似论文搜索仅支持Qdrant")
            return None
        
        try:
            # 首先获取原论文的向量
            original_point = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[paper_id],
                with_vectors=True
            )
            
            if not original_point:
                return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
            
            original_vector = original_point[0].vector
            
            # 使用原向量搜索相似论文
            search_filter = Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=self.user_id)),
                    FieldCondition(key="id", match=MatchValue(value=paper_id), is_not=True)
                ]
            )
            
            # search_result = self.client.search(
            #     collection_name=self.collection_name,
            #     query_vector=original_vector,
            #     query_filter=search_filter,
            #     limit=top_k
            # )

            search_result = self._search_qdrant(
                query=original_point[0].vector,
                mode="hybrid",
                top_k=top_k,
                filters=search_filter
            )
            
            return self._convert_qdrant_search_result(search_result)
            
        except Exception as e:
            print(f"❌ 获取相似论文失败: {e}")
            return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
    
    def get_user_statistics(self):
        """获取用户数据统计（仅Qdrant）"""
        if not self.use_qdrant:
            print("⚠️ 用户统计仅支持Qdrant")
            return {}
        
        try:
            # 获取所有用户数据点
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=self.user_id))]
                ),
                limit=10000,  # 根据实际数据调整
                with_payload=True,
                with_vectors=False
            )
            
            points = scroll_result[0]  # points是第一个元素
            
            # 统计分析
            stats = {
                "total_papers": 0,
                "total_chunks": 0,
                "venues": {},
                "years": {},
                "tasks": {},
                "methods": {}
            }
            
            paper_ids = set()
            
            for point in points:
                payload = point.payload
                metainfo = payload.get("metainfo", {})
                
                if payload.get("type") == "summary":
                    stats["total_papers"] += 1
                    paper_ids.add(point.id)
                elif payload.get("type") == "chunk":
                    stats["total_chunks"] += 1
                
                # 统计会议分布
                venue = metainfo.get("venue", "Unknown")
                stats["venues"][venue] = stats["venues"].get(venue, 0) + 1
                
                # 统计年份分布
                year = metainfo.get("year", "Unknown")
                stats["years"][str(year)] = stats["years"].get(str(year), 0) + 1
                
                # 统计任务分布
                tasks = metainfo.get("tasks", "")
                if tasks:
                    for task in tasks.split(", "):
                        stats["tasks"][task] = stats["tasks"].get(task, 0) + 1
                
                # 统计方法分布
                methods = metainfo.get("methods", "")
                if methods:
                    for method in methods.split(", "):
                        stats["methods"][method] = stats["methods"].get(method, 0) + 1
            
            return stats
            
        except Exception as e:
            print(f"❌ 获取用户统计失败: {e}")
            return {}


# 工厂函数，用于根据配置创建知识库管理器
def get_kb_manager(user_id: str = None):
    """工厂方法，根据配置返回不同的管理器"""
    return KnowledgeBaseManager(user_id=user_id)


def get_user_kb_manager():
    """获取当前用户的知识库管理器"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return KnowledgeBaseManager(user_id=user_id)