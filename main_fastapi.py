"""
FastAPI应用入口 - 从Flask最小迁移
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# 创建FastAPI应用
app = FastAPI(
    title="Academic Searcher API",
    description="学术搜索系统API - FastAPI版本",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件（等同于Flask-CORS）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并注册路由 - 必须在静态文件挂载之前
try:
    from app.api import (
        chat_router, file_router, paper_router, system_router,
        conversation_router, user_router, knowledge_router
    )
    
    # 保持与Flask版本一致的路由前缀
    app.include_router(chat_router)  # chat路由无前缀：/chat, /conversations/{conversation_id}/stream
    app.include_router(file_router, prefix="/api")  # file路由有前缀：/api/file/*
    app.include_router(paper_router, prefix="/api")  # paper路由有前缀
    app.include_router(system_router, prefix="/api")  # system路由有前缀
    app.include_router(conversation_router)  # conversation路由无前缀：/conversations/*
    app.include_router(user_router, prefix="/api")  # user路由有前缀：/api/user/*
    app.include_router(knowledge_router, prefix="/api")  # knowledge路由有前缀：/api/knowledge/*
except ImportError as e:
    print(f"⚠️ 路由导入失败: {e}")

@app.get("/")
async def index():
    """提供前端页面"""
    try:
        return FileResponse('frontend/index.html')
    except FileNotFoundError:
        return {"message": "前端文件未找到", "docs": "/docs"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """提供前端静态文件 - 处理所有非API路由"""
    # 排除API路径和文档路径
    if full_path.startswith("api/") or full_path.startswith("docs") or \
       full_path.startswith("redoc") or full_path.startswith("openapi.json") or \
       full_path.startswith("health"):
        raise HTTPException(status_code=404)
    
    file_path = os.path.join("frontend", full_path)
    
    # 如果请求的是具体文件且存在，返回该文件
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # 否则返回 index.html（SPA模式）
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"message": "前端文件未找到", "docs": "/docs"}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "framework": "FastAPI",
        "version": "1.0.0"
    }




if __name__ == "__main__":
    import uvicorn
    
    # 从环境变量获取配置
    env = os.getenv('FLASK_ENV', 'development')
    port = int(os.getenv('PORT', 5000))
    debug = env == 'development'
    
    print(f"🚀 启动学术搜索系统 (FastAPI版本)")
    print(f"   环境: {env}")
    print(f"   端口: {port}")
    print(f"   调试模式: {debug}")
    print(f"   API文档: http://localhost:{port}/docs")
    
    # 启动应用
    if debug:
        # 开发模式：使用字符串导入以支持reload
        uvicorn.run(
            "main_fastapi:app",
            host="0.0.0.0",
            port=port,
            reload=True
        )
    else:
        # 生产模式：直接使用app对象
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            reload=False
        )