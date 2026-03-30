"""
后台任务服务 - 处理论文解析等异步任务
"""

import queue
import threading
from threading import Thread
import uuid
from typing import Dict, Callable, Any

from app.core.pdf_parser import parse_pdf_to_metadata
from app.config import Config


class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        
        # 获取用户专属路径
        self.user_paths = Config.get_user_paths(self.user_id)
        
        # 解析任务队列
        self.parse_queue = queue.Queue()
        
        # 解析任务状态跟踪
        self.parse_tasks: Dict[str, Dict] = {}
        
        # 任务状态文件路径
        self.tasks_file = self.user_paths['memory_path'] / 'tasks.json'
        
        # 并发控制 - 使用线程锁而非信号量，避免资源追踪器警告
        self._parse_lock = threading.Lock()
        self._active_tasks = 0
        self._max_concurrent = Config.PARSE_SEMAPHORE
        
        # 加载已有任务状态
        self._load_tasks()
        
        # 启动工作线程
        self._start_workers()
    
    def _acquire_slot(self, timeout=1):
        """获取执行槽位（替代信号量）"""
        import time
        start = time.time()
        while True:
            with self._parse_lock:
                if self._active_tasks < self._max_concurrent:
                    self._active_tasks += 1
                    return True
            if time.time() - start > timeout:
                return False
            time.sleep(0.01)
    
    def _release_slot(self):
        """释放执行槽位"""
        with self._parse_lock:
            self._active_tasks = max(0, self._active_tasks - 1)
    
    def _start_workers(self):
        """启动工作线程"""
        for i in range(Config.PARSE_WORKERS):
            worker = Thread(target=self._parse_worker, daemon=True, name=f"ParseWorker-{i}")
            worker.start()
            print(f"🚀 启动解析工作线程 {i}")
    
    def _parse_worker(self):
        """后台解析工作线程"""
        while True:
            try:
                # 从队列获取任务
                task = self.parse_queue.get(timeout=1)
                        
            except queue.Empty:
                continue

            # 只有成功拿到任务，才进入处理流程
            try:
                task_id, pdf_path, file_id = task
                
                # 更新任务状态
                self.parse_tasks[task_id] = {"status": "processing", "message": "正在解析论文..."}
                self._save_tasks()
                
                # 使用槽位控制并发（替代信号量）
                if not self._acquire_slot(timeout=30):
                    self.parse_tasks[task_id] = {"status": "failed", "message": "等待执行超时"}
                    self._save_tasks()
                    self.parse_queue.task_done()
                    continue
                    
                try:
                    print(f"🔄 开始解析任务 {task_id}: {file_id}")
                    
                    # 执行解析
                    result = parse_pdf_to_metadata(pdf_path, file_id=file_id, output_dir=self.user_paths['parsed_papers_path'], user_id=self.user_id)
                    
                    if result.get("status") == "success":
                        self.parse_tasks[task_id] = {"status": "completed", "message": "解析成功"}
                        print(f"✅ 解析任务 {task_id} 完成")
                    else:
                        error_msg = result.get("message", "未知错误")
                        self.parse_tasks[task_id] = {"status": "failed", "message": f"解析失败: {error_msg}"}
                        print(f"❌ 解析任务 {task_id} 失败: {error_msg}")
                        
                except Exception as e:
                    self.parse_tasks[task_id] = {"status": "failed", "message": f"解析异常: {str(e)}"}
                    print(f"💥 解析任务 {task_id} 异常: {e}")
                finally:
                    self._release_slot()
                    
                # 保存任务状态
                self._save_tasks()

            except Exception as e:
                print(f"🔥 解析工作线程异常: {e}")
                # continue
            finally:
                self.parse_queue.task_done()
    
    def submit_parse_task(self, pdf_path: str, file_id: str) -> str:
        """
        提交解析任务
        Args:
            pdf_path: PDF文件路径
            file_id: 文件ID
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 添加到队列
        self.parse_queue.put((task_id, pdf_path, file_id))
        
        # 初始化任务状态
        self.parse_tasks[task_id] = {"status": "pending", "message": "等待处理..."}
        self._save_tasks()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict:
        """
        获取任务状态
        Args:
            task_id: 任务ID
        Returns:
            任务状态信息
        """
        return self.parse_tasks.get(task_id, {"status": "not_found", "message": "任务不存在"})
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        """获取所有任务状态"""
        return self.parse_tasks.copy()
    
    def clear_completed_tasks(self):
        """清除已完成的任务"""
        completed_tasks = [
            task_id for task_id, task in self.parse_tasks.items()
            if task["status"] in ["completed", "failed"]
        ]
        
        for task_id in completed_tasks:
            del self.parse_tasks[task_id]
        
        self._save_tasks()
        print(f"🧹 清除了 {len(completed_tasks)} 个已完成的任务")
    
    def _load_tasks(self):
        """加载任务状态"""
        if self.tasks_file.exists():
            try:
                import json
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    self.parse_tasks = json.load(f)
            except Exception as e:
                print(f"加载任务状态失败: {e}")
                self.parse_tasks = {}
    
    def _save_tasks(self):
        """保存任务状态"""
        try:
            import json
            # 确保目录存在
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.parse_tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务状态失败: {e}")


class AsyncTaskManager:
    """通用异步任务管理器"""
    
    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        
        self.tasks: Dict[str, Dict] = {}
        self.task_queue = queue.Queue()
        self.results: Dict[str, Any] = {}
        
        # 启动工作线程
        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def _worker(self):
        """工作线程"""
        while True:
            try:
                task_id, func, args, kwargs = self.task_queue.get(timeout=1)
                
                # 更新任务状态
                self.tasks[task_id] = {"status": "running", "message": "正在执行..."}
                
                try:
                    # 执行任务
                    result = func(*args, **kwargs)
                    
                    # 保存结果
                    self.results[task_id] = result
                    
                    # 更新任务状态
                    self.tasks[task_id] = {"status": "completed", "message": "执行完成"}
                    
                except Exception as e:
                    # 保存错误信息
                    self.results[task_id] = None
                    self.tasks[task_id] = {"status": "failed", "message": str(e)}
                
                finally:
                    self.task_queue.task_done()
                    
            except queue.Empty:
                continue
    
    def submit_task(self, func: Callable, *args, **kwargs) -> str:
        """
        提交异步任务
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 添加到队列
        self.task_queue.put((task_id, func, args, kwargs))
        
        # 初始化任务状态
        self.tasks[task_id] = {"status": "pending", "message": "等待执行..."}
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict:
        """获取任务状态"""
        return self.tasks.get(task_id, {"status": "not_found", "message": "任务不存在"})
    
    def get_task_result(self, task_id: str) -> Any:
        """获取任务结果"""
        if task_id in self.results:
            return self.results[task_id]
        return None
    
    def wait_for_task(self, task_id: str, timeout: float = None) -> Any:
        """等待任务完成并返回结果"""
        import time
        
        start_time = time.time()
        
        while True:
            status = self.get_task_status(task_id)
            
            if status["status"] == "completed":
                return self.get_task_result(task_id)
            elif status["status"] == "failed":
                raise Exception(status["message"])
            
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"任务 {task_id} 执行超时")
            
            time.sleep(0.1)


# 延迟初始化全局实例
background_task_manager = None
async_task_manager = None

def get_background_task_manager(user_id: str = None):
    """获取后台任务管理器实例（延迟初始化）"""
    global background_task_manager
    if background_task_manager is None:
        background_task_manager = BackgroundTaskManager(user_id)
    return background_task_manager

def get_async_task_manager(user_id: str = None):
    """获取异步任务管理器实例（延迟初始化）"""
    global async_task_manager
    if async_task_manager is None:
        async_task_manager = AsyncTaskManager(user_id)
    return async_task_manager

def get_user_background_task_manager():
    """获取当前用户的后台任务管理器实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return BackgroundTaskManager(user_id)

def get_user_async_task_manager():
    """获取当前用户的异步任务管理器实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return AsyncTaskManager(user_id)


def run_async_log(message: str, status: str):
    """
    异步记录日志（示例）
    Args:
        message: 日志消息
        status: 状态
    """
    def log_task():
        import time
        time.sleep(0.1)  # 模拟耗时操作
        print(f"[{status.upper()}] {message}")

    get_async_task_manager().submit_task(log_task)


async def process_pdf_full_async(pdf_path: str, file_id: str, kb_id: str, user_id: str):
    """
    完整的 PDF 异步处理任务（包含文本提取、向量化、LLM分析）
    - 第一阶段：提取文本、添加原文到向量库
    - 第二阶段：LLM分析、添加摘要到向量库

    Args:
        pdf_path: PDF 文件路径
        file_id: 文件ID
        kb_id: 知识库ID
        user_id: 用户ID
    """
    from app.services.knowledgebase_service import get_user_knowledge_base_service
    from app.core.pdf_parser import process_pdf_for_knowledge_base, analyze_and_add_summary

    try:
        kb_service = get_user_knowledge_base_service()

        # 第一阶段：文本提取和向量化
        try:
            # 更新状态为 processing
            kb_service.update_file_status(kb_id, file_id, "processing", progress=30)
            print(f"📄 开始处理 PDF: {file_id}")

            # 提取文本并添加原文到向量库
            result = process_pdf_for_knowledge_base(
                pdf_path=pdf_path,
                file_id=file_id,
                kb_id=kb_id,
                user_id=user_id
            )

            if result['status'] == 'success':
                # 更新状态为 ready（前端可以显示文档）
                kb_service.update_file_status(
                    kb_id,
                    file_id,
                    "ready",
                    chunk_count=result.get('chunk_count', 0),
                    progress=60
                )
                print(f"✅ PDF 文本处理完成: {file_id}")
            else:
                # 处理失败
                kb_service.update_file_status(
                    kb_id,
                    file_id,
                    "failed",
                    message=result.get('message', '处理失败')
                )
                print(f"❌ PDF 文本处理失败: {file_id} - {result.get('message')}")
                return

        except Exception as e:
            # 异常处理
            kb_service.update_file_status(
                kb_id,
                file_id,
                "failed",
                message=str(e)
            )
            print(f"❌ PDF 文本处理异常: {file_id} - {e}")
            return

        # 第二阶段：LLM 分析
        try:
            # 更新状态为 analyzing
            kb_service.update_file_status(kb_id, file_id, "analyzing", progress=70)
            print(f"🤖 开始 LLM 分析: {file_id}")

            # 提取 PDF 内容（用于 LLM 分析）
            from app.config import Config
            user_paths = Config.get_user_paths(user_id)
            output_dir = user_paths['parsed_papers_path']

            from app.core.pdf_parser import process_pdf
            pdf_content = process_pdf(pdf_path, output_dir)

            # 异步调用 LLM 分析并添加摘要
            summary_result = await analyze_and_add_summary(
                pdf_content=pdf_content,
                file_id=file_id,
                kb_id=kb_id,
                user_id=user_id
            )

            if summary_result['status'] == 'success':
                # 更新状态为 completed
                kb_service.update_file_status(
                    kb_id,
                    file_id,
                    "completed",
                    has_summary=True,
                    progress=100
                )
                print(f"✅ PDF 完整处理完成: {file_id}")
            else:
                # 分析失败（但文档仍然可用）
                kb_service.update_file_status(
                    kb_id,
                    file_id,
                    "ready",  # 保持 ready 状态，文档可用
                    message=f"LLM分析失败: {summary_result.get('message')}"
                )
                print(f"⚠️ LLM 分析失败: {file_id} - {summary_result.get('message')}")

        except Exception as e:
            # 异常处理（但文档仍然可用）
            kb_service.update_file_status(
                kb_id,
                file_id,
                "ready",  # 保持 ready 状态，文档可用
                message=f"LLM分析异常: {str(e)}"
            )
            print(f"❌ LLM 分析异常: {file_id} - {e}")

    except Exception as e:
        # 整体异常处理
        kb_service.update_file_status(
            kb_id,
            file_id,
            "failed",
            message=str(e)
        )
        print(f"❌ PDF 处理失败: {file_id} - {e}")


async def process_pdf_async(pdf_path: str, file_id: str, kb_id: str, user_id: str):
    """
    异步处理 PDF 文件（完整流程，已废弃，保留兼容性）
    1. 同步：提取文本并添加原文到向量库
    2. 异步：调用 LLM 分析并添加摘要

    Args:
        pdf_path: PDF 文件路径
        file_id: 文件ID
        kb_id: 知识库ID
        user_id: 用户ID

    Note: 此函数已废弃，请使用两阶段处理方式
    """
    try:
        # 1. 同步处理：提取文本并添加原文
        from app.core.pdf_parser import process_pdf_for_knowledge_base
        result = process_pdf_for_knowledge_base(
            pdf_path=pdf_path,
            file_id=file_id,
            kb_id=kb_id,
            user_id=user_id
        )

        if result['status'] == 'success':
            # 2. 异步处理：LLM 分析并添加摘要
            pdf_content = {
                'text': result['full_text'],
                'images': result.get('images', []),
                'tables': result.get('tables', [])
            }

            from app.core.pdf_parser import analyze_and_add_summary
            summary_result = await analyze_and_add_summary(
                pdf_content=pdf_content,
                file_id=file_id,
                kb_id=kb_id,
                user_id=user_id
            )

            print(f"✅ PDF 完整处理完成: {file_id}")
        else:
            print(f"⚠️ PDF 原文处理失败: {result.get('message')}")

    except Exception as e:
        print(f"❌ PDF 异步处理失败: {e}")


async def llm_analysis_async(pdf_path: str, file_id: str, kb_id: str, user_id: str):
    """
    异步 LLM 分析任务（第二阶段）
    - 调用 LLM 进行元数据分析
    - 添加摘要到向量库
    - 更新文件状态

    Args:
        pdf_path: PDF 文件路径
        file_id: 文件ID
        kb_id: 知识库ID
        user_id: 用户ID
    """
    from app.services.knowledgebase_service import get_user_knowledge_base_service
    from app.core.pdf_parser import process_pdf, analyze_and_add_summary

    try:
        # 1. 更新状态为 analyzing
        kb_service = get_user_knowledge_base_service()
        kb_service.update_file_status(kb_id, file_id, "analyzing", progress=50)
        print(f"🤖 开始 LLM 分析: {file_id}")

        # 2. 提取 PDF 内容（用于 LLM 分析）
        from app.config import Config
        user_paths = Config.get_user_paths(user_id)
        output_dir = user_paths['parsed_papers_path']

        pdf_content = process_pdf(pdf_path, output_dir)

        # 3. 异步调用 LLM 分析并添加摘要
        summary_result = await analyze_and_add_summary(
            pdf_content=pdf_content,
            file_id=file_id,
            kb_id=kb_id,
            user_id=user_id
        )

        if summary_result['status'] == 'success':
            # 4. 更新状态为 completed
            kb_service.update_file_status(
                kb_id,
                file_id,
                "completed",
                has_summary=True,
                progress=100
            )
            print(f"✅ LLM 分析完成: {file_id}")
        else:
            # 分析失败
            kb_service.update_file_status(
                kb_id,
                file_id,
                "failed",
                message=summary_result.get('message', 'LLM分析失败')
            )
            print(f"❌ LLM 分析失败: {file_id} - {summary_result.get('message')}")

    except Exception as e:
        # 异常处理
        kb_service.update_file_status(
            kb_id,
            file_id,
            "failed",
            message=str(e)
        )
        print(f"❌ LLM 分析异常: {file_id} - {e}")


# ==================== AI 生成任务管理器 ====================
from typing import List, Optional
import datetime
from pathlib import Path

class AIGenerationTaskManager:
    """AI 内容生成任务管理器 (PPT/研究报告)"""

    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        from app.config import Config

        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()

        # 获取用户专属路径
        self.user_paths = Config.get_user_paths(self.user_id)

        # AI 生成任务队列
        self.generation_queue = queue.Queue()

        # AI 生成任务状态跟踪
        self.generation_tasks: Dict[str, Dict] = {}

        # 任务状态文件路径
        self.generation_tasks_file = self.user_paths['memory_path'] / 'generation_tasks.json'

        # 任务结果目录
        self.generation_results_dir = self.user_paths['memory_path'] / 'tasks'
        self.generation_results_dir.mkdir(parents=True, exist_ok=True)

        # 并发控制 - 使用线程锁而非信号量，避免资源追踪器警告
        self._generation_lock = threading.Lock()
        self._active_generation_tasks = 0
        self._max_concurrent_generation = 2  # 最多同时处理2个生成任务

        # 加载已有任务状态
        self._load_tasks()

        # 启动工作线程
        self._start_workers()
    
    def _acquire_generation_slot(self, timeout=1):
        """获取生成任务执行槽位（替代信号量）"""
        import time
        start = time.time()
        while True:
            with self._generation_lock:
                if self._active_generation_tasks < self._max_concurrent_generation:
                    self._active_generation_tasks += 1
                    return True
            if time.time() - start > timeout:
                return False
            time.sleep(0.01)
    
    def _release_generation_slot(self):
        """释放生成任务执行槽位"""
        with self._generation_lock:
            self._active_generation_tasks = max(0, self._active_generation_tasks - 1)

    def _start_workers(self):
        """启动 AI 生成工作线程"""
        for i in range(2):  # 2个工作线程
            worker = Thread(target=self._generation_worker, daemon=True, name=f"GenerationWorker-{i}")
            worker.start()
            print(f"🚀 启动 AI 生成工作线程 {i}")

    def _generation_worker(self):
        """AI 生成工作线程"""
        while True:
            try:
                # 从队列获取任务
                task = self.generation_queue.get(timeout=1)

            except queue.Empty:
                continue

            # 只有成功拿到任务，才进入处理流程
            try:
                task_id, generation_type, query, kb_id, file_ids = task

                # 更新任务状态
                self.generation_tasks[task_id] = {
                    "status": "processing",
                    "progress": 20,
                    "message": f"正在生成{generation_type.upper()}..."
                }
                self._save_tasks()

                # 使用槽位控制并发（替代信号量）
                if not self._acquire_generation_slot(timeout=30):
                    self.generation_tasks[task_id] = {
                        "status": "failed",
                        "progress": 0,
                        "message": "等待执行超时"
                    }
                    self._save_tasks()
                    self.generation_queue.task_done()
                    continue

                try:
                    print(f"🔄 开始 AI 生成任务 {task_id}: {generation_type}")

                    # 执行生成
                    result = self._execute_generation(
                        task_id=task_id,
                        generation_type=generation_type,
                        query=query,
                        kb_id=kb_id,
                        file_ids=file_ids
                    )

                    if result.get("status") == "success":
                        self.generation_tasks[task_id] = {
                            "status": "completed",
                            "progress": 100,
                            "message": f"{generation_type.upper()}生成成功",
                            "result_path": result.get("result_path"),
                            "metadata": result.get("metadata", {})
                        }
                        print(f"✅ AI 生成任务 {task_id} 完成")
                    else:
                        error_msg = result.get("message", "未知错误")
                        self.generation_tasks[task_id] = {
                            "status": "failed",
                            "progress": 0,
                            "message": f"{generation_type.upper()}生成失败: {error_msg}"
                        }
                        print(f"❌ AI 生成任务 {task_id} 失败: {error_msg}")

                except Exception as e:
                    self.generation_tasks[task_id] = {
                        "status": "failed",
                        "progress": 0,
                        "message": f"{generation_type.upper()}生成异常: {str(e)}"
                    }
                    print(f"💥 AI 生成任务 {task_id} 异常: {e}")
                finally:
                    self._release_generation_slot()

                # 保存任务状态
                self._save_tasks()

            except Exception as e:
                print(f"🔥 AI 生成工作线程异常: {e}")
            finally:
                self.generation_queue.task_done()

    def _execute_generation(self, task_id: str, generation_type: str, query: str,
                           kb_id: str, file_ids: list[str]) -> Dict:
        """
        执行 AI 生成任务

        Args:
            task_id: 任务ID
            generation_type: 生成类型 (ppt/report)
            query: 用户查询/主题描述
            kb_id: 知识库ID
            file_ids: 选中的文件ID列表

        Returns:
            生成结果
        """
        try:
            # 更新进度
            self.generation_tasks[task_id]["progress"] = 40
            self.generation_tasks[task_id]["message"] = "正在检索相关文档..."
            self._save_tasks()

            # 从向量库检索相关文档片段
            from app.core.kb_manager import get_kb_manager
            kb_manager = get_kb_manager(user_id=self.user_id)

            relevant_chunks = kb_manager.search_in_files(
                query=query,
                file_ids=file_ids,
                kb_id=kb_id,
                top_k=10
            )

            if not relevant_chunks:
                return {
                    "status": "failed",
                    "message": "未找到相关文档内容"
                }

            # 更新进度
            self.generation_tasks[task_id]["progress"] = 60
            self.generation_tasks[task_id]["message"] = "正在生成内容..."
            self._save_tasks()

            # 调用生成器
            if generation_type == "ppt":
                from app.core.ppt_generator import generate_ppt
                # content = await generate_ppt()
                content = "# PPT\n\n## 模板内容\n\n待实现..."
            elif generation_type == "report":
                # TODO: 实现研究报告生成
                content = "# 研究报告\n\n## 模板内容\n\n待实现..."
            else:
                return {
                    "status": "failed",
                    "message": f"不支持的生成类型: {generation_type}"
                }

            # 保存生成结果
            result_filename = f"{task_id}_{generation_type}.md"
            result_path = self.generation_results_dir / result_filename

            with open(result_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 更新进度
            self.generation_tasks[task_id]["progress"] = 90
            self._save_tasks()

            # 返回成功结果
            return {
                "status": "success",
                "result_path": str(result_path),
                "metadata": {
                    "generation_type": generation_type,
                    "file_count": len(file_ids),
                    "content_length": len(content),
                    "chunk_count": len(relevant_chunks)
                }
            }

        except Exception as e:
            print(f"❌ 执行生成任务失败: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }

    def submit_generation_task(self, generation_type: str, query: str,
                               kb_id: str, file_ids: List[str]) -> str:
        """
        提交 AI 生成任务

        Args:
            generation_type: 生成类型 (ppt/report)
            query: 用户查询/主题描述
            kb_id: 知识库ID
            file_ids: 选中的文件ID列表

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())

        # 添加到队列
        self.generation_queue.put((task_id, generation_type, query, kb_id, file_ids))

        # 初始化任务状态
        self.generation_tasks[task_id] = {
            "task_id": task_id,
            "user_id": self.user_id,
            "kb_id": kb_id,
            "generation_type": generation_type,
            "file_ids": file_ids,
            "query": query,
            "status": "pending",
            "progress": 0,
            "message": "等待处理...",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_tasks()

        print(f"📝 AI 生成任务已提交: {task_id} ({generation_type})")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        return self.generation_tasks.get(task_id)

    def get_user_tasks(self, kb_id: str = None, status: str = None) -> List[Dict]:
        """
        获取用户的所有任务

        Args:
            kb_id: 知识库ID（可选，用于过滤）
            status: 任务状态（可选，用于过滤）

        Returns:
            任务列表
        """
        tasks = list(self.generation_tasks.values())

        # 按 kb_id 过滤
        if kb_id:
            tasks = [t for t in tasks if t.get("kb_id") == kb_id]

        # 按状态过滤
        if status:
            tasks = [t for t in tasks if t.get("status") == status]

        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        if task_id not in self.generation_tasks:
            return False

        # 删除任务
        del self.generation_tasks[task_id]

        # 保存任务状态
        self._save_tasks()

        print(f"🗑️ 任务已删除: {task_id}")
        return True

    def get_task_result(self, task_id: str) -> Optional[str]:
        """
        获取任务结果内容

        Args:
            task_id: 任务ID

        Returns:
            任务结果内容（Markdown格式）
        """
        task = self.generation_tasks.get(task_id)
        if not task or task.get("status") != "completed":
            return None

        result_path = task.get("result_path")
        if not result_path or not Path(result_path).exists():
            return None

        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ 读取任务结果失败: {e}")
            return None

    def _load_tasks(self):
        """加载任务状态"""
        if self.generation_tasks_file.exists():
            try:
                import json
                with open(self.generation_tasks_file, 'r', encoding='utf-8') as f:
                    self.generation_tasks = json.load(f)
            except Exception as e:
                print(f"加载 AI 生成任务状态失败: {e}")
                self.generation_tasks = {}

    def _save_tasks(self):
        """保存任务状态"""
        try:
            import json
            # 确保目录存在
            self.generation_tasks_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.generation_tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.generation_tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存 AI 生成任务状态失败: {e}")


# 延迟初始化全局实例
ai_generation_task_manager = None

def get_ai_generation_task_manager(user_id: str = None):
    """获取 AI 生成任务管理器实例（延迟初始化）"""
    global ai_generation_task_manager
    if ai_generation_task_manager is None:
        ai_generation_task_manager = AIGenerationTaskManager(user_id)
    return ai_generation_task_manager

def get_user_ai_generation_task_manager():
    """获取当前用户的 AI 生成任务管理器实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return AIGenerationTaskManager(user_id)