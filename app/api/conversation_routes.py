"""
论文对话相关路由 - FastAPI版本
从Flask版本最小迁移
"""

from fastapi import APIRouter, Request

from app.services.chat_service import get_chat_service
from app.services.conversation_service import get_conversation_service
from app.models.schemas import BaseResponse

router = APIRouter()

# ==================== 会话管理API ====================

@router.post("/conversations")
async def create_conversation(request: Request):
    """创建新对话 - 从Flask版本迁移"""
    try:
        data = await request.json()
        title = data.get('title', '新对话')
        
        chat_service = get_conversation_service()
        result = chat_service.create_conversation(title)
        
        if result['status'] == 'success':
            return {
                "status": "success",
                "message": "对话创建成功",
                "conversation": result['conversation']
            }
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '创建失败')
            ).model_dump(), 400
            
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"创建对话失败: {str(e)}"
        ).model_dump(), 500


@router.get("/conversations")
async def get_conversations(request: Request):
    """获取对话列表 - 从Flask版本迁移"""
    try:
        include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
        
        chat_service = get_conversation_service()
        result = chat_service.get_conversations(include_deleted)
        
        if result['status'] == 'success':
            return {
                "status": "success",
                "conversations": result['conversations'],
                "count": result['count']
            }
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '获取失败')
            ).model_dump(), 400
            
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"获取对话列表失败: {str(e)}"
        ).model_dump(), 500


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取指定对话 - 从Flask版本迁移"""
    try:
        chat_service = get_conversation_service()
        result = chat_service.get_conversation_by_id(conversation_id)
        
        if result['status'] == 'success':
            return {
                "status": "success",
                "conversation": result['conversation']
            }
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '对话不存在')
            ).model_dump(), 404
            
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"获取对话失败: {str(e)}"
        ).model_dump(), 500


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话 - 从Flask版本迁移"""
    try:
        chat_service = get_conversation_service()
        result = chat_service.delete_conversation(conversation_id)
        
        if result['status'] == 'success':
            return BaseResponse(
                status="success",
                message="对话删除成功"
            ).model_dump()
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '删除失败')
            ).model_dump(), 400
            
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"删除对话失败: {str(e)}"
        ).model_dump(), 500


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """获取对话消息 - 从Flask版本迁移"""
    try:
        chat_service = get_conversation_service()
        result = chat_service.get_conversation_messages(conversation_id)
        
        if result['status'] == 'success':
            return {
                "status": "success",
                "messages": result['messages'],
                "conversation_id": conversation_id
            }
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '获取消息失败')
            ).model_dump(), 404
            
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"获取对话消息失败: {str(e)}"
        ).model_dump(), 500


@router.post("/paper/conversation/start")
async def start_conversation(request: Request):
    """开始论文对话 - 从Flask版本迁移"""
    try:
        data = await request.json()
        if not data or 'paper_id' not in data or 'paper_name' not in data:
            return BaseResponse(
                status="error",
                message="缺少参数"
            ).model_dump(), 400
        
        paper_id = data['paper_id']
        paper_name = data['paper_name']
        
        # 开始新的论文对话会话
        conversation = get_chat_service().conversation_manager.start_conversation(paper_id, paper_name)
        
        return {
            "status": "success",
            "data": {
                "paper_id": paper_id,
                "paper_name": paper_name,
                "created_at": conversation['created_at']
            }
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"开始对话失败: {str(e)}"
        ).model_dump(), 500


@router.post("/paper/conversation/end")
async def end_conversation(request: Request):
    """结束论文对话 - 从Flask版本迁移"""
    try:
        data = await request.json()
        if not data or 'paper_id' not in data:
            return BaseResponse(
                status="error",
                message="缺少paper_id参数"
            ).model_dump(), 400
        
        paper_id = data['paper_id']
        
        # 结束论文对话会话
        success = get_chat_service().conversation_manager.end_conversation(paper_id)
        
        if success:
            return BaseResponse(
                status="success",
                message="对话已结束"
            ).model_dump()
        else:
            return BaseResponse(
                status="error",
                message="对话不存在"
            ).model_dump(), 404
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"结束对话失败: {str(e)}"
        ).model_dump(), 500


@router.get("/paper/conversation/history/{paper_id}")
async def get_conversation_history(paper_id: str):
    """获取论文对话历史 - 从Flask版本迁移"""
    try:
        history = get_conversation_service().get_conversation_history(paper_id)
        
        return {
            "status": "success",
            "data": {
                "paper_id": paper_id,
                "history": [msg.model_dump() for msg in history]
            }
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"获取历史失败: {str(e)}"
        ).model_dump(), 500