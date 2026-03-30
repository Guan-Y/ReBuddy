"""
搜索服务 - 处理深度研究等搜索相关业务
"""

from typing import Generator, Dict, Any

from app.core.searcher import DeepResearcher, default_researcher
from app.core.kb_manager import get_kb_manager
from app.models.schemas import SearchRequest


class SearchService:
    """搜索服务"""
    
    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        self.researcher = default_researcher
        # 懒加载：不立即创建kb_manager，在需要时创建
        self._kb_manager = None
    
    @property
    def kb_manager(self):
        """懒加载获取知识库管理器"""
        if self._kb_manager is None:
            from app.core.kb_manager import get_kb_manager
            self._kb_manager = get_kb_manager(user_id=self.user_id)
        return self._kb_manager
    
    def deep_research(self, query: str, max_steps: int = 8) -> Generator[str, None, None]:
        """
        深度研究
        Args:
            query: 研究查询
            max_steps: 最大步数
        Returns:
            生成器，产生研究步骤和结果
        """
        return self.researcher.research(query, max_steps)
    
    def search_knowledge_base(self, query: str, mode: str = "hybrid", top_k: int = 3, filters: Dict = None) -> Dict:
        """
        搜索知识库
        Args:
            query: 查询内容
            mode: 搜索模式 (summary/detail/hybrid)
            top_k: 返回结果数量
            filters: 过滤条件
        Returns:
            搜索结果
        """
        return self.kb_manager.search(query=query, mode=mode, top_k=top_k, filters=filters)
    
    def search_by_paper_id(self, query: str, paper_id: str, top_k: int = 5) -> Dict:
        """
        基于论文ID的精确检索
        Args:
            query: 查询内容
            paper_id: 论文ID
            top_k: 返回结果数量
        Returns:
            检索结果
        """
        return self.kb_manager.search_by_paper_id(query=query, paper_id=paper_id, top_k=top_k)
    
    def semantic_search(self, query: str, filters: Dict = None, top_k: int = 10) -> Dict:
        """
        语义搜索
        Args:
            query: 查询内容
            filters: 过滤条件（如年份、会议、作者等）
            top_k: 返回结果数量
        Returns:
            搜索结果
        """
        return self.kb_manager.search(query=query, mode="summary", top_k=top_k, filters=filters)
    
    def hybrid_search(self, query: str, top_k: int = 5) -> Dict:
        """
        混合搜索（结合语义和关键词）
        Args:
            query: 查询内容
            top_k: 返回结果数量
        Returns:
            搜索结果
        """
        return self.kb_manager.search(query=query, mode="hybrid", top_k=top_k)
    
    def get_similar_papers(self, paper_id: str, top_k: int = 5) -> Dict:
        """
        获取相似论文
        Args:
            paper_id: 论文ID
            top_k: 返回结果数量
        Returns:
            相似论文列表
        """
        # 首先获取原论文的信息
        paper_info = self.kb_manager.paper_collection.get(ids=[paper_id])
        
        if not paper_info['ids']:
            return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
        
        # 使用原论文的文档内容进行相似性搜索
        original_doc = paper_info['documents'][0]
        
        return self.kb_manager.paper_collection.query(
            query_texts=original_doc,
            n_results=top_k + 1,  # +1 因为会包含自己
            where={"paper_id": {"$ne": paper_id}}  # 排除自己
        )
    
    def search_papers_by_filters(self, filters: Dict, top_k: int = 20) -> Dict:
        """
        根据过滤条件搜索论文
        Args:
            filters: 过滤条件
            top_k: 返回结果数量
        Returns:
            搜索结果
        """
        # 构建一个通用查询来获取所有论文，然后应用过滤器
        dummy_query = "research"  # 通用查询词
        
        return self.kb_manager.search(
            query=dummy_query,
            mode="summary",
            top_k=top_k,
            filters=filters
        )
    
    def build_search_filters(self, 
                           year_range: tuple = None,
                           venues: list = None,
                           authors: list = None,
                           tasks: list = None,
                           methods: list = None,
                           has_code: bool = None) -> Dict:
        """
        构建搜索过滤器
        Args:
            year_range: 年份范围 (min_year, max_year)
            venues: 会议/期刊列表
            authors: 作者列表
            tasks: 任务列表
            methods: 方法列表
            has_code: 是否有代码
        Returns:
            过滤器字典
        """
        filters = {}
        
        if year_range:
            min_year, max_year = year_range
            filters["year"] = {"$gte": min_year, "$lte": max_year}
        
        if venues:
            venue_conditions = [{"$contains": venue} for venue in venues]
            if len(venue_conditions) == 1:
                filters["venue"] = venue_conditions[0]
            else:
                filters["$or"] = [{"venue": cond} for cond in venue_conditions]
        
        if authors:
            author_conditions = [{"$contains": author} for author in authors]
            if len(author_conditions) == 1:
                filters["authors"] = author_conditions[0]
            else:
                if "$or" not in filters:
                    filters["$or"] = []
                filters["$or"].extend([{"authors": cond} for cond in author_conditions])
        
        if tasks:
            task_conditions = [{"$contains": task} for task in tasks]
            if len(task_conditions) == 1:
                filters["tasks"] = task_conditions[0]
            else:
                if "$or" not in filters:
                    filters["$or"] = []
                filters["$or"].extend([{"tasks": cond} for cond in task_conditions])
        
        if methods:
            method_conditions = [{"$contains": method} for method in methods]
            if len(method_conditions) == 1:
                filters["methods"] = method_conditions[0]
            else:
                if "$or" not in filters:
                    filters["$or"] = []
                filters["$or"].extend([{"methods": cond} for cond in method_conditions])
        
        if has_code is not None:
            filters["has_code"] = has_code
        
        return filters


# 延迟初始化全局服务实例
search_service = None

def get_search_service(user_id: str = None):
    """获取搜索服务实例（延迟初始化）"""
    global search_service
    if search_service is None:
        search_service = SearchService(user_id)
    return search_service

def get_user_search_service():
    """获取当前用户的搜索服务实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return SearchService(user_id)