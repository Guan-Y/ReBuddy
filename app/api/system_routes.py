"""
系统相关路由 - FastAPI版本
从Flask版本最小迁移
"""

from fastapi import APIRouter
from datetime import datetime

from app.services.chat_service import get_chat_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "conversation_count": len(get_chat_service().get_conversation_history())
    }


@router.get("/version")
async def get_version():
    """获取版本信息"""
    return {
        "status": "success",
        "version": "1.0.0",
        "architecture": "modular_monolith",
        "framework": "FastAPI"
    }


@router.get("/config")
async def get_config():
    """获取公开配置信息"""
    return {
        "status": "success",
        "config": {
            "max_file_size": "16MB",
            "supported_formats": [".pdf"],
            "max_parse_workers": 2,
            "features": [
                "chat",
                "paper_analysis", 
                "knowledge_base",
                "deep_research"
            ]
        }
    }


@router.get("/stats")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        from app.services.file_service import get_user_file_service
        from app.services.background_tasks import get_user_background_task_manager
        
        # 获取文件统计
        file_service = get_user_file_service()
        file_stats = file_service.get_file_stats()
        
        # 获取任务统计
        task_manager = get_user_background_task_manager()
        task_stats = task_manager.get_task_stats()
        
        return {
            "status": "success",
            "stats": {
                "files": file_stats,
                "tasks": task_stats,
                "uptime": "N/A",  # 可以后续添加
                "memory_usage": "N/A"  # 可以后续添加
            }
        }
        
    except Exception as e:
        return {
            "status": "success",
            "stats": {
                "files": {"total": 0, "papers": 0},
                "tasks": {"pending": 0, "processing": 0, "completed": 0},
                "error": str(e)
            }
        }


@router.post("/system/cleanup")
async def system_cleanup():
    """系统清理"""
    try:
        from app.services.file_service import get_user_file_service
        from app.services.background_tasks import get_user_background_task_manager
        
        # 清理临时文件
        file_service = get_user_file_service()
        cleanup_result = file_service.cleanup_temp_files()
        
        # 清理已完成的任务
        task_manager = get_user_background_task_manager()
        task_cleanup_result = task_manager.cleanup_completed_tasks()
        
        return {
            "status": "success",
            "cleanup": {
                "files": cleanup_result,
                "tasks": task_cleanup_result
            }
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"清理失败: {str(e)}"
        ).model_dump(), 500