"""
Pydantic模型定义 - 用于请求/响应校验
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# 文件状态枚举
class FileStatus(str, Enum):
    """文件处理状态"""
    UPLOADING = "uploading"  # 上传中
    PROCESSING = "processing"  # 解析中（文本提取、向量化）
    READY = "ready"  # 就绪（前端可显示文档）
    ANALYZING = "analyzing"  # LLM分析中
    COMPLETED = "completed"  # 完成（包含摘要）
    FAILED = "failed"  # 失败


# 请求模型
class ChatRequest(BaseModel):
    query: str = Field(..., description="用户查询内容")
    net: bool = Field(default=False, description="是否使用网络搜索")
    kb: bool = Field(default=False, description="是否使用知识库")
    deep: bool = Field(default=False, description="是否使用深度研究")
    paper_id: Optional[str] = Field(default=None, description="论文ID（论文问答时使用）")
    conversation_id: Optional[str] = Field(default=None, description="对话ID（多对话窗口时使用）")


class FileListRequest(BaseModel):
    pass


class FolderCreateRequest(BaseModel):
    folderName: str = Field(..., description="文件夹名称")
    parentID: Optional[str] = Field(default="root", description="父节点ID")


class FileDeleteRequest(BaseModel):
    id: str = Field(..., description="文件/文件夹ID")


class FileRenameRequest(BaseModel):
    id: str = Field(..., description="文件/文件夹ID")
    newName: str = Field(..., description="新名称")


class SearchRequest(BaseModel):
    keywords: str = Field(..., description="搜索关键词")


# 响应模型
class BaseResponse(BaseModel):
    status: str = Field(..., description="状态：success/error")
    message: Optional[str] = Field(default=None, description="消息")


class FileStatusResponse(BaseModel):
    """文件状态响应"""
    file_id: str = Field(..., description="文件ID")
    status: FileStatus = Field(..., description="文件状态")
    progress: int = Field(default=0, description="进度百分比 (0-100)")
    message: Optional[str] = Field(default=None, description="状态消息")
    chunk_count: Optional[int] = Field(default=None, description="已添加的文本片段数量")
    has_summary: bool = Field(default=False, description="是否有AI摘要")


class FileStatusListResponse(BaseResponse):
    """批量文件状态响应"""
    files: List[FileStatusResponse] = Field(..., description="文件状态列表")


class ChatResponse(BaseResponse):
    response: Optional[str] = Field(default=None, description="AI响应内容")
    processing_time: Optional[float] = Field(default=None, description="处理时间（秒）")
    query_length: Optional[int] = Field(default=None, description="查询长度")


class ChatStreamResponse(BaseModel):
    chunk: Optional[str] = Field(default=None, description="流式响应片段")
    full_response: Optional[str] = Field(default=None, description="完整响应")
    status: Optional[str] = Field(default=None, description="状态：complete/error")


class FileNode(BaseModel):
    id: str = Field(..., description="节点ID")
    name: str = Field(..., description="名称")
    type: str = Field(..., description="类型：file/folder")
    path: str = Field(..., description="路径")
    size: Optional[int] = Field(default=None, description="文件大小")
    upload_time: Optional[str] = Field(default=None, description="上传时间")
    children: Optional[List['FileNode']] = Field(default_factory=list, description="子节点")


class FileListResponse(BaseResponse):
    data: List[FileNode] = Field(..., description="文件树数据")


class PaperInfo(BaseModel):
    id: str = Field(..., description="论文ID")
    title: str = Field(..., description="标题")
    authors: str = Field(..., description="作者")
    year: str = Field(..., description="年份")
    abstract: str = Field(..., description="摘要")


class PaperMetadata(PaperInfo):
    """论文元数据（继承自 PaperInfo，扁平化结构）"""

    # === 扩展基础信息 ===
    venue: str = Field(default="", description="发表会议或期刊")
    citation_count: str = Field(default="N/A", description="引用次数")
    code_url: str = Field(default="", description="GitHub代码链接")
    has_code: bool = Field(default=False, description="是否有代码")

    # === 语义标签 ===
    tasks: str = Field(default="", description="核心任务（逗号分隔）")
    methods: str = Field(default="", description="方法流派（逗号分隔）")
    domains: str = Field(default="", description="应用领域（逗号分隔）")
    datasets: str = Field(default="", description="数据集名称（逗号分隔）")

    # === 核心逻辑 ===
    problem: str = Field(default="", description="研究痛点/Research Gap")
    contribution: str = Field(default="", description="核心创新点（分号分隔）")
    metrics: str = Field(default="", description="关键性能指标（分号分隔）")

    # === 专家批判 ===
    ablation: str = Field(default="", description="消融实验发现")
    limitations: str = Field(default="", description="局限性（分号分隔）")
    compute: str = Field(default="", description="计算资源")

    # === 知识链接 ===
    baselines: str = Field(default="", description="对比模型（分号分隔）")
    foundations: str = Field(default="", description="基础理论（分号分隔）")

    # === 资产统计 ===
    asset_images_count: int = Field(default=0, description="图片数量")
    asset_tables_count: int = Field(default=0, description="表格数量")

    # === 资产路径（仅用于内部处理）===
    image_paths: List[str] = Field(default_factory=list, description="图片路径列表")
    table_paths: List[str] = Field(default_factory=list, description="表格路径列表")

    # === summary 字段（保留，与 abstract 同义，用于兼容）===
    summary: str = Field(default="", description="精简的文章摘要（与 abstract 同义）")


class SearchResponse(BaseResponse):
    papers: List[PaperInfo] = Field(..., description="推荐论文列表")


class HealthResponse(BaseModel):
    status: str = Field(..., description="健康状态")
    timestamp: str = Field(..., description="时间戳")
    conversation_count: int = Field(..., description="对话数量")


class HistoryMessage(BaseModel):
    timestamp: str = Field(..., description="时间戳")
    content: str = Field(..., description="内容")
    type: str = Field(..., description="类型：user/ai")


class HistoryResponse(BaseResponse):
    history: List[HistoryMessage] = Field(..., description="对话历史")


# 解析任务模型
class ParseTask(BaseModel):
    task_id: str
    file_id: str
    pdf_path: str
    status: str = Field(default="pending", description="状态：pending/processing/completed/failed")
    message: str = Field(default="", description="状态消息")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# 用户模型
class User(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None


# 会话模型
class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    paper_id: Optional[str] = None
    title: str
    messages: List[HistoryMessage] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    window_position: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# 多对话窗口管理请求模型
class ConversationCreateRequest(BaseModel):
    title: str = Field(..., description="对话标题")
    paper_id: Optional[str] = Field(default=None, description="关联的论文ID")


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="对话标题")
    is_active: Optional[bool] = Field(default=None, description="是否活跃")
    window_position: Optional[int] = Field(default=None, description="窗口位置")


class ConversationListResponse(BaseResponse):
    conversations: List[Conversation] = Field(..., description="对话列表")


class ConversationDetailResponse(BaseResponse):
    conversation: Conversation = Field(..., description="对话详情")


# 解决前向引用
FileNode.model_rebuild()


# ==================== AI内容生成模型 ====================

class AIGenerationRequest(BaseModel):
    """AI内容生成请求"""
    query: str = Field(..., description="用户查询/主题描述")
    kb_id: str = Field(..., description="知识库ID")
    file_ids: List[str] = Field(..., description="选中的文件ID列表")
    generation_type: Literal["ppt", "report"] = Field(..., description="生成类型：ppt/report")


class AIGenerationResponse(BaseResponse):
    """AI内容生成响应"""
    task_id: Optional[str] = Field(default=None, description="异步任务ID")
    content: Optional[str] = Field(default=None, description="生成的内容（Markdown格式）")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据（幻灯片数量、字数等）")


class AIGenerationTaskStatus(BaseModel):
    """异步任务状态"""
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = Field(default=0, description="进度百分比")
    message: Optional[str] = Field(default=None)
    result: Optional[Dict[str, Any]] = Field(default=None)


# ==================== 文件对话模型 ====================

class FileChatRequest(BaseModel):
    """文件对话请求"""
    query: str = Field(..., description="用户查询")
    use_kb: bool = Field(default=False, description="是否使用知识库其他文件辅助")


class FileChatStreamResponse(BaseModel):
    """文件流式对话响应"""
    chunk: Optional[str] = Field(default=None, description="流式片段")
    full_response: Optional[str] = Field(default=None, description="完整响应")
    status: Optional[str] = Field(default=None, description="状态：complete/error")


class FileDetailResponse(BaseResponse):
    """文件详情响应（阅读器用）"""
    data: Optional[Dict[str, Any]] = Field(default=None, description="文件详细信息")


# ==================== AI 生成任务模型 ====================

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败


class AIGenerationTask(BaseModel):
    """AI 生成任务模型"""
    task_id: str = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")
    kb_id: str = Field(..., description="知识库ID")
    generation_type: Literal["ppt", "report"] = Field(..., description="生成类型")
    file_ids: List[str] = Field(..., description="选中的文件ID列表")
    query: str = Field(..., description="用户查询/主题描述")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    message: Optional[str] = Field(default=None, description="状态消息")
    result_path: Optional[str] = Field(default=None, description="结果文件路径")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class TaskListResponse(BaseResponse):
    """任务列表响应"""
    data: Optional[Dict[str, Any]] = Field(default=None, description="任务列表数据")
    # data 结构: { "kb_id": str, "tasks": List[AIGenerationTask], "total": int }


class TaskDetailResponse(BaseResponse):
    """任务详情响应"""
    data: Optional[AIGenerationTask] = Field(default=None, description="任务详情")
    result_content: Optional[str] = Field(default=None, description="结果内容（仅已完成任务）")