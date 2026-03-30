"""
论文服务 - 处理论文相关业务逻辑
"""

from typing import List, Dict, Optional

from app.core.kb_manager import get_kb_manager
from app.models.schemas import PaperInfo


class PaperService:
    """论文服务"""
    
    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        # 懒加载：不立即创建kb_manager，在需要时创建
        self._kb_manager = None
    
    @property
    def kb_manager(self):
        """懒加载获取知识库管理器"""
        if self._kb_manager is None:
            from app.core.kb_manager import get_kb_manager
            self._kb_manager = get_kb_manager(user_id=self.user_id)
        return self._kb_manager
    
    def recommend_papers(self, keywords: str) -> List[PaperInfo]:
        """
        根据关键词推荐论文
        Args:
            keywords: 关键词
        Returns:
            推荐论文列表
        """
    
        # 使用知识库搜索相关论文
        results = self.kb_manager.search(
            query=keywords,
            mode="summary",
            top_k=5
        )
        
        papers = []
        if results and results['metadatas'][0]:
            for i, metadata in enumerate(results['metadatas'][0]):
                paper = PaperInfo(
                    id=metadata.get('paper_id', ''),
                    title=metadata.get('title', ''),
                    authors=metadata.get('authors', ''),
                    year=str(metadata.get('year', '')),
                    abstract=metadata.get('contribution', '')[:200] + '...'
                )
                papers.append(paper)
        
        # 如果知识库中没有足够的结果，添加一些示例推荐
        if len(papers) < 3:
            papers.extend(self._get_sample_recommendations())
        
        return papers[:5]  # 最多返回5个推荐
    
    def _get_sample_recommendations(self) -> List[PaperInfo]:
        """获取示例推荐论文"""
        return [
            PaperInfo(
                id='p2',
                title='Recommendation Systems with Graph Neural Networks',
                authors='He et al.',
                year='2023',
                abstract='图神经网络在推荐系统中的应用综述，重点介绍消息传递机制与负采样策略...'
            ),
            PaperInfo(
                id='p3',
                title='Retrieval-Augmented Generation for Knowledge-Intensive NLP',
                authors='Lewis et al.',
                year='2020',
                abstract='提出 RAG 框架，将检索与生成相结合，在开放域问答等任务上取得突破...'
            )
        ]
    
    def search_papers(self, query: str, filters: Dict = None, top_k: int = 10) -> Dict:
        """
        搜索论文
        Args:
            query: 查询内容
            filters: 过滤条件
            top_k: 返回数量
        Returns:
            搜索结果
        """
        results = self.kb_manager.search(
            query=query,
            mode="summary",
            top_k=top_k,
            filters=filters
        )
        
        return results


# 延迟初始化全局服务实例
paper_service = None

def get_paper_service(user_id: str = None):
    """获取论文服务实例（延迟初始化）"""
    global paper_service
    if paper_service is None:
        paper_service = PaperService(user_id)
    return paper_service

def get_user_paper_service():
    """获取当前用户的论文服务实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return PaperService(user_id)