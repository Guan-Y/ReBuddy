"""
用户管理API路由 - FastAPI版本
从Flask版本最小迁移
"""

from fastapi import APIRouter, Request, HTTPException

from app.services.user_service import get_user_service
from app.core.user_context import UserContext

router = APIRouter()


@router.post("/user/login")
async def login(request: Request):
    """用户登录 - 从Flask版本迁移"""
    try:
        data = await request.json()
        username = data.get('username')
        
        if not username:
            raise HTTPException(status_code=400, detail='用户名不能为空')
        
        user_service = get_user_service()
        user = user_service.get_user(username)
        
        if not user:
            try:
                # 自动创建新用户
                user = user_service.create_user(username, data.get('display_name'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # 更新最后登录时间
        user_service.update_last_login(username)
        
        # 设置会话
        UserContext.set_current_user_id(username)
        
        return {
            'user': user,
            'message': '登录成功'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/user/logout")
async def logout():
    """用户登出 - 从Flask版本迁移"""
    try:
        UserContext.clear_user_context()
        return {'message': '登出成功'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登出失败: {str(e)}")


@router.get("/user/current")
async def get_current_user():
    """获取当前用户信息 - 从Flask版本迁移"""
    try:
        user_id = UserContext.get_current_user_id()
        user_service = get_user_service()
        user = user_service.get_user(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail='用户不存在')
        
        return {'user': user}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.post("/user/create")
async def create_user(request: Request):
    """创建新用户 - 从Flask版本迁移"""
    try:
        data = await request.json()
        username = data.get('username')
        display_name = data.get('display_name')
        
        if not username:
            raise HTTPException(status_code=400, detail='用户名不能为空')
        
        user_service = get_user_service()
        try:
            user = user_service.create_user(username, display_name)
            return {'user': user, 'message': '用户创建成功'}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")


@router.get("/user/list")
async def list_users():
    """列出所有用户 - 从Flask版本迁移"""
    try:
        user_service = get_user_service()
        users = user_service.list_users()
        return {'users': users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.delete("/user/delete/{user_id}")
async def delete_user(user_id: str):
    """删除用户 - 从Flask版本迁移"""
    try:
        user_service = get_user_service()
        success = user_service.delete_user(user_id)
        
        if success:
            return {'message': '用户删除成功'}
        else:
            raise HTTPException(status_code=404, detail='用户不存在')
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")