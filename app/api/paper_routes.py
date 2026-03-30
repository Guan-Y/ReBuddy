"""
论文相关路由 - FastAPI版本
从Flask版本最小迁移
"""

from fastapi import APIRouter, Request

from app.services.paper_service import get_paper_service
from app.models.schemas import BaseResponse, SearchResponse, SearchRequest

router = APIRouter()


@router.post("/search")
async def search_papers(request: Request):
    """论文推荐接口"""
    try:
        data = await request.json()
        
        if not data or 'keywords' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400
        
        # 构建请求对象
        keywords = data.get('keywords', '')
        assert isinstance(keywords, str) or isinstance(keywords, list), "关键词必须是字符串或字符串列表"

        if isinstance(keywords, list):
            keywords = ' '.join(keywords)
        
        search_request = SearchRequest(keywords=keywords)
        
        if not search_request.keywords:
            return BaseResponse(
                status="error",
                message="关键词不能为空"
            ).model_dump(), 400
        
        # 推荐论文
        papers = get_paper_service().recommend_papers(search_request.keywords)
        
        return SearchResponse(
            status="success",
            papers=papers
        ).model_dump()
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.get("/papers/{paper_id}")
async def get_paper_detail(paper_id: str):
    """获取论文详情"""
    try:
        paper_detail = get_paper_service().get_paper_detail(paper_id)
        
        if paper_detail:
            return {
                "status": "success",
                "paper": paper_detail
            }
        else:
            return BaseResponse(
                status="error",
                message="论文不存在"
            ).model_dump(), 404
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.post("/papers/{paper_id}/chat")
async def chat_with_paper(paper_id: str, request: Request):
    """与论文对话"""
    try:
        data = await request.json()
        
        if not data or 'query' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400
        
        query = data['query'].strip()
        if not query:
            return BaseResponse(
                status="error",
                message="查询内容不能为空"
            ).model_dump(), 400
        
        # 论文对话
        result = get_paper_service().chat_with_paper(paper_id, query)
        
        if result['status'] == 'success':
            return {
                "status": "success",
                "response": result['response'],
                "paper_id": paper_id
            }
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '对话失败')
            ).model_dump(), 500
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.get("/papers")
async def list_papers():
    """获取论文列表"""
    try:
        papers = get_paper_service().list_papers()
        
        return {
            "status": "success",
            "papers": papers
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """删除论文"""
    try:
        success = get_paper_service().delete_paper(paper_id)
        
        if success:
            return BaseResponse(
                status="success",
                message="论文删除成功"
            ).model_dump()
        else:
            return BaseResponse(
                status="error",
                message="论文删除失败"
            ).model_dump(), 400
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500