"""
知识库管理相关路由 - FastAPI版本
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json

from app.services.knowledgebase_service import get_user_knowledge_base_service
from app.models.schemas import BaseResponse, AIGenerationRequest
import os
from pathlib import Path
from app.core.user_context import UserContext
from app.core.kb_manager import get_kb_manager

router = APIRouter()


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求"""
    name: str
    description: Optional[str] = ""


class KnowledgeBaseResponse(BaseResponse):
    """知识库响应"""
    data: Optional[dict] = None


class KnowledgeBaseListResponse(BaseResponse):
    """知识库列表响应"""
    data: Optional[List[dict]] = None


@router.get("/knowledge/bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases():
    """获取知识库列表"""
    try:
        kb_service = get_user_knowledge_base_service()
        knowledge_bases = kb_service.list_knowledge_bases()
        
        return KnowledgeBaseListResponse(
            status="success",
            data=knowledge_bases
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/base", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(request: KnowledgeBaseCreateRequest):
    """创建知识库"""
    try:
        if not request.name or not request.name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        kb_service = get_user_knowledge_base_service()
        new_kb = kb_service.create_knowledge_base(
            name=request.name.strip(),
            description=request.description.strip()
        )
        
        return KnowledgeBaseResponse(
            status="success",
            data=new_kb
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files", response_model=KnowledgeBaseListResponse)
async def get_knowledge_base_files(kb_id: str):
    """获取知识库下的文件列表"""
    try:
        kb_service = get_user_knowledge_base_service()
        files = kb_service.get_knowledge_base_files(kb_id)
        
        return KnowledgeBaseListResponse(
            status="success",
            data=files
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/base/{kb_id}/upload", response_model=KnowledgeBaseResponse)
async def upload_file_to_knowledge_base(kb_id: str, file: UploadFile = File(...)):
    """上传文件到知识库（快速返回，异步处理）"""
    try:
        # 1. 获取当前用户ID
        user_id = UserContext.get_current_user_id()
        kb_service = get_user_knowledge_base_service()

        # 2. 保存文件到知识库目录
        kb_files_dir = kb_service.kb_root / kb_id / "files"
        kb_files_dir.mkdir(parents=True, exist_ok=True)

        file_content = await file.read()
        file_path = kb_files_dir / file.filename

        # 处理文件名冲突
        counter = 1
        original_path = file_path
        while file_path.exists():
            name, ext = os.path.splitext(str(original_path))
            file_path = Path(f"{name}_{counter}{ext}")
            counter += 1

        with open(file_path, "wb") as f:
            f.write(file_content)

        # 3. 添加文件记录到知识库（初始状态：uploading）
        file_info = {
            "name": file_path.name,
            "original_name": file.filename,
            "size": len(file_content),
            "type": file.content_type or "unknown",
            "file_path": str(file_path),
            "relative_path": f"files/{file_path.name}"
        }

        file_record = kb_service.add_file_to_knowledge_base(kb_id, file_info)

        # 4. 对于支持的文件类型，触发异步处理任务
        supported_extensions = {'.pdf', '.md', '.txt', '.csv', '.xlsx', '.docx'}
        file_ext = Path(file.filename).suffix.lower()

        if file_ext in supported_extensions:
            # 异步处理：文本提取 + 向量化 + LLM分析
            from app.services.background_tasks import process_pdf_full_async
            import asyncio
            asyncio.create_task(process_pdf_full_async(
                pdf_path=str(file_path),
                file_id=file_record['id'],
                kb_id=kb_id,
                user_id=user_id
            ))
        else:
            # 不支持的文件类型，直接标记为 ready
            kb_service.update_file_status(kb_id, file_record['id'], "ready", progress=100)

        # 5. 快速返回响应（前端立即看到文件）
        return KnowledgeBaseResponse(
            status="success",
            data=file_record
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/base/{kb_id}", response_model=KnowledgeBaseResponse)
async def delete_knowledge_base(kb_id: str):
    """删除知识库（包括向量库数据）"""
    try:
        user_id = UserContext.get_current_user_id()
        kb_service = get_user_knowledge_base_service()
        
        # 1. 获取知识库中的所有文件
        files = kb_service.get_knowledge_base_files(kb_id)
        
        # 2. 从向量库中删除所有文件的数据（指定 kb_id）
        from app.core.kb_manager import get_kb_manager
        kb_manager = get_kb_manager(user_id=user_id)
        
        for file_record in files:
            file_id = file_record.get('id')
            if file_id:
                kb_manager.delete_paper(file_id, kb_id=kb_id)
        
        # 3. 删除知识库目录和元数据
        success = kb_service.delete_knowledge_base(kb_id)
        
        return KnowledgeBaseResponse(
            status="success",
            message=f"知识库删除成功（已清理 {len(files)} 个文件的向量库数据）"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base_detail(kb_id: str):
    """获取知识库详情"""
    try:
        kb_service = get_user_knowledge_base_service()
        kb_detail = kb_service.get_knowledge_base_detail(kb_id)
        
        if kb_detail is None:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        return KnowledgeBaseResponse(
            status="success",
            data=kb_detail
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/base/{kb_id}/files/{file_id}", response_model=KnowledgeBaseResponse)
async def delete_file_from_knowledge_base(kb_id: str, file_id: str):
    """从知识库删除文件（包括向量库数据）"""
    try:
        # import pdb; pdb.set_trace()
        kb_service = get_user_knowledge_base_service()
        user_id = UserContext.get_current_user_id()
        
        # 1. 从向量库中删除对应的论文数据（指定 kb_id）
        from app.core.kb_manager import get_kb_manager
        kb_manager = get_kb_manager(user_id=user_id)
        kb_manager.delete_paper(file_id, kb_id=kb_id)
        
        # 2. 获取文件路径并删除物理文件
        file_path = kb_service.get_kb_file_path(kb_id, file_id)
        if file_path and file_path.exists():
            file_path.unlink()
        
        # 3. 从知识库元数据中移除文件记录
        success = kb_service.remove_file_from_knowledge_base(kb_id, file_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return KnowledgeBaseResponse(
            status="success",
            message="文件删除成功（包括向量库数据）"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files/{file_id}/content")
async def get_file_content(kb_id: str, file_id: str, request: Request):
    """获取文件完整内容"""
    try:
        kb_service = get_user_knowledge_base_service()
        content = kb_service.get_file_content(kb_id, file_id)
        
        if content is None:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 根据文件类型设置正确的Content-Type
        file_info = kb_service.get_file_info(kb_id, file_id)
        content_type = "application/octet-stream"
        is_pdf = False
        if file_info:
            from pathlib import Path
            file_ext = Path(file_info["name"]).suffix.lower()
            content_type_map = {
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.md': 'text/markdown'
            }
            content_type = content_type_map.get(file_ext, 'application/octet-stream')
            is_pdf = file_ext == '.pdf'
        
        # 检查是否是预览请求（通过查询参数或Referer判断）
        preview_mode = request.query_params.get('preview', 'false').lower() == 'true'
        referer = request.headers.get('referer', '')
        is_iframe_request = 'iframe' in referer.lower() or preview_mode
        
        from fastapi.responses import Response
        headers = {}
        
        # 如果是PDF且在iframe中显示，使用inline；否则使用attachment
        if is_pdf and is_iframe_request:
            headers["Content-Disposition"] = f'inline; filename="{file_info["name"] if file_info else "file"}"'
            headers["Accept-Ranges"] = "bytes"
            headers["Cache-Control"] = "no-cache"
            headers["X-Content-Type-Options"] = "nosniff"
        else:
            headers["Content-Disposition"] = f'attachment; filename="{file_info["name"] if file_info else "file"}"'
        
        return Response(
            content=content,
            media_type=content_type,
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files/{file_id}/text")
async def get_file_text_content(kb_id: str, file_id: str):
    """获取文件文本内容"""
    try:
        kb_service = get_user_knowledge_base_service()
        text_content = kb_service.get_file_text_content(kb_id, file_id)
        
        if text_content is None:
            raise HTTPException(status_code=404, detail="文件不存在或无法读取文本内容")
        
        return {"status": "success", "data": {"text": text_content}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files/{file_id}/info")
async def get_file_info(kb_id: str, file_id: str):
    """获取文件详细信息"""
    try:
        kb_service = get_user_knowledge_base_service()
        file_info = kb_service.get_file_info(kb_id, file_id)
        
        if file_info is None:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return {"status": "success", "data": file_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/conversation/history")
async def get_kb_conversation_history(kb_id: str):
    """获取知识库对话历史"""
    try:
        from app.core.conversation_manager import get_conversation_manager
        
        conversation_manager = get_conversation_manager()
        
        # 获取知识库对话历史
        history = conversation_manager.get_kb_history(kb_id)
        
        # 转换为可序列化格式
        messages = [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in history]
        
        return {
            "status": "success",
            "data": {
                "kb_id": kb_id,
                "messages": messages
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/base/{kb_id}/conversation")
async def clear_kb_conversation(kb_id: str):
    """清除知识库对话"""
    try:
        from app.core.conversation_manager import get_conversation_manager

        conversation_manager = get_conversation_manager()
        success = conversation_manager.clear_kb_conversation(kb_id)

        if success:
            return {
                "status": "success",
                "message": "对话清除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="知识库对话不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files/{file_id}/status")
async def get_file_status(kb_id: str, file_id: str):
    """获取单个文件的处理状态"""
    try:
        kb_service = get_user_knowledge_base_service()
        status_info = kb_service.get_file_status(kb_id, file_id)

        if status_info is None:
            raise HTTPException(status_code=404, detail="文件不存在")

        return {
            "status": "success",
            "data": status_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files/status")
async def get_all_file_statuses(kb_id: str):
    """获取知识库中所有文件的处理状态"""
    try:
        kb_service = get_user_knowledge_base_service()
        statuses = kb_service.get_all_file_statuses(kb_id)

        return {
            "status": "success",
            "data": {
                "kb_id": kb_id,
                "files": statuses
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI内容生成接口 ====================

@router.post("/knowledge/base/{kb_id}/generate")
async def generate_ai_content(kb_id: str, request: AIGenerationRequest):
    """
    生成AI内容（PPT或研究报告）

    支持两种模式：
    1. 同步模式：直接返回生成结果（适合快速生成）
    2. 异步模式：返回task_id，通过轮询获取结果（适合耗时较长的生成）
    """
    try:
        from app.services.generation_service import GenerationService

        # 参数校验
        if request.kb_id != kb_id:
            raise HTTPException(status_code=400, detail="知识库ID不匹配")

        if not request.file_ids:
            raise HTTPException(status_code=400, detail="请至少选择一个文件")

        # TODO: 实现生成逻辑
        generation_service = GenerationService()

        if request.generation_type == "ppt":
            # 生成PPT
            content = generation_service.generate_ppt(
                query=request.query,
                kb_id=request.kb_id,
                file_ids=request.file_ids
            )
        else:
            # 生成研究报告
            content = generation_service.generate_report(
                query=request.query,
                kb_id=request.kb_id,
                file_ids=request.file_ids
            )

        return {
            "status": "success",
            "content": content,
            "metadata": {
                "generation_type": request.generation_type,
                "file_count": len(request.file_ids)
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/generation/{task_id}/status")
async def get_generation_task_status(task_id: str):
    """查询生成任务状态"""
    try:
        # TODO: 实现任务状态查询逻辑
        from app.services.generation_service import GenerationService

        generation_service = GenerationService()
        status_info = generation_service.get_task_status(task_id)

        if status_info is None:
            raise HTTPException(status_code=404, detail="任务不存在")

        return {
            "status": "success",
            "data": status_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文件对话接口 ====================

@router.get("/knowledge/base/{kb_id}/files/{file_id}/detail")
async def get_file_detail(kb_id: str, file_id: str):
    """
    获取文件详情（用于阅读器视图）

    返回内容：
    - 基本信息：文件名、大小、类型、上传时间
    - 预览URL：用于iframe加载PDF
    - 处理状态：是否已解析完成
    - 元数据：PDF解析后的摘要、作者、年份等（如果有）
    """
    try:
        kb_service = get_user_knowledge_base_service()

        # 获取文件基本信息
        file_info = kb_service.get_file_info(kb_id, file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 获取文件处理状态
        status_info = kb_service.get_file_status(kb_id, file_id)

        # 构建预览URL（与pdfViewer保持一致）
        preview_url = f"/api/file/view?id={file_id}"

        # 获取文件元数据（如果有）
        metadata = {}
        if status_info and status_info.get('has_summary'):
            # 从向量库获取文件元数据
            kb_manager = get_kb_manager(user_id=UserContext.get_current_user_id())
            paper_meta = kb_manager.get_paper_metadata(file_id)
            if paper_meta:
                metadata = {
                    'title': paper_meta.get('title', ''),
                    'authors': paper_meta.get('authors', ''),
                    'year': paper_meta.get('year', ''),
                    'abstract': paper_meta.get('abstract', ''),
                    'contribution': paper_meta.get('contribution', ''),
                }

        return {
            "status": "success",
            "data": {
                "id": file_id,
                "kb_id": kb_id,
                "name": file_info.get('name', ''),
                "original_name": file_info.get('original_name', ''),
                "size": file_info.get('size', 0),
                "type": file_info.get('type', ''),
                "upload_time": file_info.get('upload_time', ''),
                "preview_url": preview_url,
                "status": status_info.get('status', 'unknown'),
                "progress": status_info.get('progress', 0),
                "has_summary": status_info.get('has_summary', False),
                "metadata": metadata
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/base/{kb_id}/files/{file_id}/chat/stream")
async def chat_with_file_stream(kb_id: str, file_id: str, request: Request):
    """基于文件的流式对话，支持联网搜索"""
    try:
        # 验证请求数据
        data = await request.json()
        if not data or 'query' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400

        query = data.get('query', '').strip()
        use_kb = data.get('use_kb', False)
        use_net = data.get('net', False)  # 新增：接收联网搜索参数

        if not query:
            raise HTTPException(status_code=400, detail="查询内容不能为空")

        def generate():
            try:
                from app.services.chat_service import get_chat_service

                chat_service = get_chat_service()
                response_stream = chat_service.process_file_chat_stream(
                    query=query,
                    kb_id=kb_id,
                    file_id=file_id,
                    use_kb=use_kb,
                    use_net=use_net  # 新增：传递联网搜索参数
                )

                full_response = ""
                chunk_count = 0

                # 流式输出
                for chunk in response_stream:
                    full_response += chunk
                    chunk_count += 1
                    yield f"data: {json.dumps({'chunk': chunk, 'full_response': full_response})}\n"

                # 发送完成信号
                print(f"✅ 文件对话流式发送完成，共 {chunk_count} 个 chunk，总长度: {len(full_response)}")
                yield f"data: {json.dumps({'status': 'complete', 'full_response': full_response})}\n"

            except Exception as e:
                print(f"❌ 文件对话流式生成错误: {e}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/files/{file_id}/conversation/history")
async def get_file_conversation_history(kb_id: str, file_id: str):
    """获取文件对话历史"""
    try:
        from app.core.conversation_manager import get_conversation_manager

        conversation_manager = get_conversation_manager()

        # 获取文件对话历史
        history = conversation_manager.get_file_history(kb_id, file_id)

        # 转换为可序列化格式
        messages = [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in history]

        return {
            "status": "success",
            "data": {
                "kb_id": kb_id,
                "file_id": file_id,
                "messages": messages
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/base/{kb_id}/files/{file_id}/conversation")
async def clear_file_conversation(kb_id: str, file_id: str):
    """清除文件对话"""
    try:
        from app.core.conversation_manager import get_conversation_manager

        conversation_manager = get_conversation_manager()
        success = conversation_manager.clear_file_conversation(kb_id, file_id)

        if success:
            return {
                "status": "success",
                "message": "文件对话清除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="文件对话不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI 内容生成接口（任务管理）====================

@router.post("/knowledge/base/{kb_id}/generate")
async def generate_ai_content(kb_id: str, request: AIGenerationRequest):
    """
    生成AI内容（PPT或研究报告）

    支持异步模式：返回task_id，通过轮询获取结果
    """
    try:
        from app.services.generation_service import GenerationService

        # 参数校验
        if request.kb_id != kb_id:
            raise HTTPException(status_code=400, detail="知识库ID不匹配")

        if not request.file_ids:
            raise HTTPException(status_code=400, detail="请至少选择一个文件")

        # 提交生成任务
        generation_service = GenerationService()
        task_id = generation_service.submit_generation_task(
            generation_type=request.generation_type,
            query=request.query,
            kb_id=request.kb_id,
            file_ids=request.file_ids
        )

        return {
            "status": "success",
            "task_id": task_id,
            "message": "AI生成任务已提交，请使用task_id查询进度"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/generation/{task_id}/status")
async def get_generation_task_status(task_id: str):
    """查询生成任务状态"""
    try:
        from app.services.generation_service import GenerationService

        generation_service = GenerationService()
        status_info = generation_service.get_task_status(task_id)

        if status_info is None:
            raise HTTPException(status_code=404, detail="任务不存在")

        return {
            "status": "success",
            "data": status_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/base/{kb_id}/tasks")
async def get_user_tasks(kb_id: str, status: Optional[str] = None):
    """
    获取用户的所有任务

    Query Parameters:
        status: 任务状态过滤（可选：pending/processing/completed/failed）
    """
    try:
        from app.services.generation_service import GenerationService
        # import pdb; pdb.set_trace()

        generation_service = GenerationService()
        tasks = generation_service.get_user_tasks(kb_id=kb_id, status=status)

        # 只返回进行中和已完成的任务
        filtered_tasks = [
            t for t in tasks
            if t.get("status") in ["processing", "completed"]
        ]

        return {
            "status": "success",
            "data": {
                "kb_id": kb_id,
                "tasks": filtered_tasks,
                "total": len(filtered_tasks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/generation/{task_id}/detail")
async def get_task_detail(task_id: str):
    """获取任务详情"""
    try:
        from app.services.generation_service import GenerationService

        generation_service = GenerationService()
        task_info = generation_service.get_task_status(task_id)

        if task_info is None:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 如果任务已完成，获取结果内容
        if task_info.get("status") == "completed":
            result_content = generation_service.get_task_result(task_id)
            task_info["result_content"] = result_content

        return {
            "status": "success",
            "data": task_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/generation/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    try:
        from app.services.generation_service import GenerationService

        generation_service = GenerationService()
        success = generation_service.delete_task(task_id)

        if success:
            return {
                "status": "success",
                "message": "任务已删除"
            }
        else:
            raise HTTPException(status_code=404, detail="任务不存在")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/generation/{task_id}/download")
async def download_task_result(task_id: str):
    """下载任务结果"""
    try:
        from app.services.generation_service import GenerationService

        generation_service = GenerationService()

        # 检查任务状态
        task_info = generation_service.get_task_status(task_id)
        if task_info is None:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task_info.get("status") != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成，无法下载")

        # 获取结果内容
        result_content = generation_service.get_task_result(task_id)
        if result_content is None:
            raise HTTPException(status_code=404, detail="任务结果不存在")

        # 获取文件名
        generation_type = task_info.get("generation_type", "unknown")
        filename = f"{task_id}_{generation_type}.md"

        # 返回文件
        from fastapi.responses import Response
        return Response(
            content=result_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))