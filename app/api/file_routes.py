"""
文件管理相关路由 - FastAPI版本
从Flask版本最小迁移
"""

import tempfile
import os
from pathlib import Path
from fastapi import APIRouter, Request, File, UploadFile
from fastapi.responses import FileResponse
from werkzeug.utils import secure_filename

from app.services.file_service import get_user_file_service
from app.services.background_tasks import get_user_background_task_manager
from app.models.schemas import (
    BaseResponse, FileListResponse, FolderCreateRequest, 
    FileDeleteRequest, FileRenameRequest
)
router = APIRouter()


@router.get("/file/list")
async def list_files():
    """获取文件树列表"""
    try:
        tree = get_user_file_service().list_files()
        
        return FileListResponse(
            status="success",
            data=tree
        ).model_dump()
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.post("/folder")
async def create_folder(request: Request):
    """新建文件夹"""
    try:
        data = await request.json()
        
        if not data or 'folderName' not in data:
            return BaseResponse(
                status="error",
                message="缺少参数"
            ).model_dump(), 400
        
        # 构建请求对象
        folder_request = FolderCreateRequest(
            folderName=data['folderName'].strip(),
            parentID=data.get('parentID', 'root')
        )
        
        if not folder_request.folderName:
            return BaseResponse(
                status="error",
                message="文件夹名称不能为空"
            ).model_dump(), 400
        
        # 创建文件夹
        new_folder = get_user_file_service().create_folder(
            parent_id=folder_request.parentID,
            folder_name=folder_request.folderName
        )
        
        return {
            "status": "success",
            "data": new_folder
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.delete("/file")
async def delete_file(request: Request):
    """删除文件或文件夹"""
    try:
        data = await request.json()
        
        if not data or 'id' not in data:
            return BaseResponse(
                status="error",
                message="缺少ID参数"
            ).model_dump(), 400
        
        file_id = data['id']
        
        success = get_user_file_service().delete_node(file_id)
        
        if success:
            return BaseResponse(
                status="success",
                message="删除成功"
            ).model_dump()
        else:
            return BaseResponse(
                status="error",
                message="删除失败"
            ).model_dump(), 400
            
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.put("/file/rename")
async def rename_file(request: Request):
    """重命名文件或文件夹"""
    try:
        data = await request.json()
        
        if not data or 'id' not in data or 'newName' not in data:
            return BaseResponse(
                status="error",
                message="缺少参数"
            ).model_dump(), 400
        
        file_id = data['id']
        new_name = data['newName'].strip()
        
        if not new_name:
            return BaseResponse(
                status="error",
                message="新名称不能为空"
            ).model_dump(), 400
        
        # 重命名文件
        renamed_node = get_user_file_service().rename_node(file_id, new_name)
        
        return {
            "status": "success",
            "data": renamed_node
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.post("/file/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """上传文件"""
    try:
        if not file.filename:
            return BaseResponse(
                status="error",
                message="没有选择文件"
            ).model_dump(), 400
        
        # 获取表单数据
        form_data = await request.form()
        parent_path = form_data.get('parentPath', '/')
        
        # 检查文件类型
        allowed_extensions = ['.pdf', '.txt', '.md']
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return BaseResponse(
                status="error",
                message=f"不支持的文件类型，仅支持: {', '.join(allowed_extensions)}"
            ).model_dump(), 400
        
        # 上传文件
        file_service = get_user_file_service()
        uploaded_file = await file_service.async_upload_file(parent_path, file)
        
        # 如果是PDF文件，启动解析任务
        if file.filename.lower().endswith('.pdf'):
            file_id = uploaded_file['id']
            pdf_path = file_service.storage_root / uploaded_file['path'].lstrip('/')
            
            task_id = get_user_background_task_manager().submit_parse_task(
                str(pdf_path),
                file_id
            )
            
            # 在响应中返回任务ID
            uploaded_file['parse_task_id'] = task_id
        
        return {
            "status": "success",
            "data": uploaded_file
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.get("/file/{file_id}/content")
async def get_file_content(file_id: str):
    """获取文件内容"""
    try:
        file_content = get_user_file_service().get_file_content(file_id)
        return file_content
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.post("/file/parse")
async def parse_file(request: Request):
    """解析文件（PDF等）"""
    try:
        data = await request.json()
        
        if not data or 'file_id' not in data:
            return BaseResponse(
                status="error",
                message="缺少文件ID参数"
            ).model_dump(), 400
        
        file_id = data['file_id']
        
        # 提交解析任务
        task_manager = get_user_background_task_manager()
        task_id = task_manager.submit_parse_task(file_id)
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": "解析任务已提交"
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.get("/file/parse/status/{task_id}")
async def get_parse_status(task_id: str):
    """获取解析任务状态"""
    try:
        task_manager = get_user_background_task_manager()
        task_status = task_manager.get_task_status(task_id)
        
        if task_status:
            return {
                "status": "success",
                "task": task_status
            }
        else:
            return BaseResponse(
                status="error",
                message="任务不存在"
            ).model_dump(), 404
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.get("/file/view")
async def view_file(request: Request):
    """查看文件（兼容旧接口）"""
    try:
        file_id = request.query_params.get('id')
        if not file_id:
            return BaseResponse(
                status="error",
                message="缺少文件ID"
            ).model_dump(), 400
        
        file_path = get_user_file_service().get_file_content(file_id)
        full_path = file_path.parent / file_path.name
        
        # 根据文件扩展名设置正确的Content-Type
        import mimetypes
        media_type, _ = mimetypes.guess_type(str(full_path))
        
        # 更强的PDF检测逻辑
        is_pdf = False
        if file_path.name.lower().endswith('.pdf'):
            is_pdf = True
        elif media_type == 'application/pdf':
            is_pdf = True
        else:
            # 通过文件头检测PDF
            try:
                with open(full_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        is_pdf = True
                        media_type = 'application/pdf'
            except Exception:
                pass
        
        # 确保PDF文件有正确的Content-Type
        if is_pdf:
            media_type = 'application/pdf'
        
        # 创建FileResponse并设置正确的响应头
        response = FileResponse(
            path=str(full_path),
            filename=file_path.name,
            media_type=media_type
        )
        
        # 设置响应头确保PDF在浏览器中显示而不是下载
        if is_pdf:
            response.headers["Content-Disposition"] = f'inline; filename="{file_path.name}"'
            response.headers["Accept-Ranges"] = "bytes"
            response.headers["Cache-Control"] = "no-cache"
            # 确保浏览器不会尝试下载
            response.headers["X-Content-Type-Options"] = "nosniff"
            
            # 添加额外的响应头确保PDF显示
            response.headers["Content-Transfer-Encoding"] = "binary"
            response.headers["Content-Type"] = "application/pdf"
        
        # 调试信息
        print(f"文件: {file_path.name}")
        print(f"检测到MIME类型: {media_type}")
        print(f"是否为PDF: {is_pdf}")
        print(f"响应头Content-Disposition: {response.headers.get('Content-Disposition', 'None')}")
        
        return response
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500


@router.get("/file/download/{file_id}")
async def download_file(file_id: str):
    """下载文件"""
    try:
        file_path = get_user_file_service().get_file_path(file_id)
        
        if not file_path or not file_path.exists():
            return BaseResponse(
                status="error",
                message="文件不存在"
            ).model_dump(), 404
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=str(e)
        ).model_dump(), 500