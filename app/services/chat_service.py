"""
聊天服务 - 从原AIProcessor和对话管理逻辑重构
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Generator

from app.core.llm_client import LLMClient, default_client
from app.core.kb_manager import KnowledgeBaseManager
from app.core.searcher import paper_survey
from app.core.conversation_manager import ConversationManager, get_conversation_manager
from app.models.schemas import ChatRequest, ChatStreamResponse, HistoryMessage


class ChatService:
    """聊天服务主类"""
    
    def __init__(self, user_id: str = None):
        from app.core.user_context import UserContext
        
        # 获取用户ID
        self.user_id = user_id or UserContext.get_current_user_id()
        
        self.llm_client = default_client
        # 使用单例模式获取 ConversationManager 实例
        self.conversation_manager = get_conversation_manager(self.user_id)
        self.kb_manager = KnowledgeBaseManager(user_id=self.user_id)

    
    def process_conversation_query_stream(self, 
                                          conversation_id: str, 
                                          query: str, 
                                          use_kb: bool=False, 
                                          use_web: bool=False) -> Generator[str, None, None]:
        """
        在指定通用对话中处理查询（流式）
        不支持深度研究模式
        """
        try:
            # 获取对话信息
            conversation = self.conversation_manager.get_conversation_by_id(conversation_id)
            # import pdb; pdb.set_trace()  # --- IGNORE ---
            if not conversation:
                yield json.dumps({"status": "error", "message": "对话不存在"})
                return
            
            # 获取对话历史（已经是字典格式）
            history = conversation.get('messages', [])
            
            # 调用通用聊天流式接口（仅支持知识库）
            response_stream = self._general_chat_stream(query, history, use_kb=use_kb, use_web=use_web)
            
            full_response = ""
            
            # 流式输出
            for chunk in response_stream:
                chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += chunk_content
                yield json.dumps({"chunk": chunk_content, "full_response": full_response})
            
            # 保存消息到对话
            self.conversation_manager.add_message_to_conversation(conversation_id, query, 'user')
            self.conversation_manager.add_message_to_conversation(conversation_id, full_response, 'ai')
            
            # 发送完成信号
            yield json.dumps({"status": "complete", "full_response": full_response})
            
        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)})
    
    
    def _general_chat(self, query: str, history: List[Dict], use_kb: bool, use_web: bool) -> str:
        """通用聊天（非流式）"""
        context = ""
        
        if use_kb:
            # 使用知识库检索
            kb_result = self.kb_manager.search(query=query, mode="hybrid", top_k=3)
            if kb_result and kb_result['documents'][0]:
                metadatas = kb_result['metadatas'][0]
                docs = kb_result['documents'][0]
                kb_content = ''
                for i in range(len(docs)):
                    kb_content += f"知识库内容 {i+1}：\n{docs[i]}\n来源论文：\n{metadatas[i]}\n"
                context += kb_content
        
        # 调用LLM（history 已经是字典格式）
        response = self.llm_client.chat_completion(
            query=query,
            context=context,
            history=history,
            stream=False
        )
        
        return response
    
    def _general_chat_stream(self, query: str, history: List[Dict], use_kb: bool, use_web: bool):
        """通用聊天（流式）"""
        context = ""
        
        if use_kb:
            # 使用知识库检索
            kb_result = self.kb_manager.search(query=query, mode="hybrid", top_k=10)
            if kb_result and kb_result['documents'][0]:
                metadatas = kb_result['metadatas'][0]
                docs = kb_result['documents'][0]
                kb_content = ''
                for i in range(len(docs)):
                    kb_content += f"知识库内容 {i+1}：\n{docs[i]}\n来源论文：\n{metadatas[i]}\n"
                print(kb_content)
                context += kb_content
        
        # 调用LLM流式接口（history 已经是字典格式）
        return self.llm_client.chat_completion(
            query=query,
            context=context,
            history=history,
            stream=True
        )
    
    
    def _kb_chat_stream(self, query: str, kb_id: str, file_ids: List[str], history: List[Dict], use_net: bool = False):
        """
        基于知识库和指定文件的流式对话

        Args:
            query: 用户查询
            kb_id: 知识库ID
            file_ids: 文件ID列表（可以为空）
            history: 对话历史（字典格式）
            use_net: 是否使用联网搜索

        Returns:
            流式响应生成器
        """
        context_parts = []

        # 如果没有选择文件，不使用知识库，直接调用LLM
        if not file_ids or len(file_ids) == 0:
            print("💬 未选择文件，不使用知识库")

            # 如果启用了联网搜索，执行网络搜索
            if use_net:
                from app.core.searcher import default_web_searcher

                print(f"🌐 执行联网搜索: {query}")
                try:
                    web_results = default_web_searcher.search(query, num_results=3)

                    if web_results:
                        web_context = default_web_searcher.format_results_as_context(web_results)
                        context_parts.append(web_context)
                        print(f"✅ 搜索到 {len(web_results)} 个网络结果")
                    else:
                        print("⚠️ 未搜索到网络结果")
                except Exception as e:
                    print(f"❌ 网络搜索失败: {e}")

            # 合并上下文
            context = "\n\n".join(context_parts) if context_parts else ""

            return self.llm_client.chat_completion(
                query=query,
                context=context,
                history=history,  # history 已经是字典格式
                stream=True
            )

        # 使用知识库检索指定文件
        kb_result = self.kb_manager.search_by_file_ids(
            query=query,
            kb_id=kb_id,
            file_ids=file_ids,
            top_k=10
        )

        if kb_result and kb_result['documents'][0]:
            metadatas = kb_result['metadatas'][0]
            docs = kb_result['documents'][0]
            kb_content = ''
            for i in range(len(docs)):
                kb_content += f"知识库内容 {i+1}：\n{docs[i]}\n来源文件：{metadatas[i]}\n"
            print(f"📚 检索到 {len(docs)} 个相关片段\n\n{kb_content}")
            context_parts.append(kb_content)
        else:
            print("⚠️ 未检索到相关内容")

        # 如果启用了联网搜索，执行网络搜索
        if use_net:
            from app.core.searcher import default_web_searcher

            print(f"🌐 执行联网搜索: {query}")
            try:
                web_results = default_web_searcher.search(query, num_results=3)

                if web_results:
                    web_context = default_web_searcher.format_results_as_context(web_results)
                    context_parts.append(web_context)
                    print(f"✅ 搜索到 {len(web_results)} 个网络结果")
                else:
                    print("⚠️ 未搜索到网络结果")
            except Exception as e:
                print(f"❌ 网络搜索失败: {e}")

        # 合并上下文
        context = "\n\n".join(context_parts) if context_parts else ""

        # 调用LLM流式接口
        return self.llm_client.chat_completion(
            query=query,
            context=context,
            history=history,  # history 已经是字典格式
            stream=True
        )
    
    def process_kb_chat_stream(self, query: str, kb_id: str, kb_name: str, file_ids: List[str], use_net: bool = False):
        """
        处理知识库对话流式请求（包含历史获取和保存）
        
        Args:
            query: 用户查询
            kb_id: 知识库ID
            kb_name: 知识库名称
            file_ids: 文件ID列表（可以为空）
            use_net: 是否使用联网搜索
        
        Returns:
            流式响应生成器
        """
        # 从知识库对话历史中获取历史消息
        messages = self.conversation_manager.get_kb_history(kb_id)
        
        # 转换为字典格式（llm_client 期望的格式）
        history = []
        for msg in messages:
            # msg 是 HistoryMessage 对象，转换为字典
            if hasattr(msg, 'model_dump'):
                history.append(msg.model_dump())
            else:
                # 兼容旧格式，直接使用字典
                history.append(msg)
        
        print(f"📚 开始知识库对话，历史消息数: {len(history)}，联网搜索: {use_net}")
        
        # 调用知识库对话流式方法
        response_stream = self._kb_chat_stream(query, kb_id, file_ids, history, use_net)
        
        # 收集完整响应
        full_response = ""
        chunk_count = 0
        
        # 流式输出
        for chunk in response_stream:
            chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            full_response += chunk_content
            chunk_count += 1
            # print(f"🔧 Service 生成 chunk {chunk_count}: {len(chunk_content)} 字符")
            yield chunk_content
        
        print(f"✅ Service 生成完成，共 {chunk_count} 个 chunk")

        # 保存消息到知识库对话历史
        self.conversation_manager.add_kb_message(kb_id, kb_name, query, 'user')
        self.conversation_manager.add_kb_message(kb_id, kb_name, full_response, 'ai')

    def _file_chat_stream(self, query: str, kb_id: str, file_id: str, use_kb: bool, history: List[Dict], use_net: bool = False):
        """
        文件级对话流式实现

        Args:
            query: 用户查询
            kb_id: 知识库ID
            file_id: 当前文件ID
            use_kb: 是否使用知识库其他文件辅助
            history: 对话历史
            use_net: 是否使用联网搜索

        Returns:
            流式响应生成器
        """
        context_parts = []

        # 1. 基于当前文件进行精确检索
        kb_result = self.kb_manager.search_by_file_ids(
            query=query,
            kb_id=kb_id,
            file_ids=[file_id],  # 只检索当前文件
            top_k=5
        )

        # 2. 如果启用了知识库辅助，额外检索知识库中的其他文件
        if use_kb and kb_result:
            # 获取知识库中的所有文件ID（排除当前文件）
            from app.services.knowledgebase_service import get_user_knowledge_base_service
            kb_service = get_user_knowledge_base_service()
            all_files = kb_service.get_knowledge_base_files(kb_id)
            other_file_ids = [f['id'] for f in all_files if f['id'] != file_id]

            if other_file_ids:
                # 检索其他文件的相关内容
                kb_result_other = self.kb_manager.search_by_file_ids(
                    query=query,
                    kb_id=kb_id,
                    file_ids=other_file_ids,
                    top_k=3
                )

                # 合并检索结果（当前文件优先）
                if kb_result_other and kb_result_other['documents'][0]:
                    kb_result['documents'][0].extend(kb_result_other['documents'][0])
                    kb_result['metadatas'][0].extend(kb_result_other['metadatas'][0])

        # 3. 如果检索无结果，回退到普通检索
        if not kb_result or not kb_result['documents'][0]:
            print("文件检索无结果，回退到普通检索")
            kb_result = self.kb_manager.search(query=query, mode="hybrid", top_k=3)

        # 4. 构建知识库上下文
        if kb_result and kb_result['documents'][0]:
            metadatas = kb_result['metadatas'][0]
            docs = kb_result['documents'][0]
            kb_content = ''
            for i in range(len(docs)):
                file_name = metadatas[i].get('file_name', '未知文件')
                kb_content += f"【文件内容 {i+1} - {file_name}】\n{docs[i]}\n"
            print(f"📄 文件对话检索到 {len(docs)} 个片段")
            context_parts.append(kb_content)

        # 5. 如果启用了联网搜索，执行网络搜索
        if use_net:
            from app.core.searcher import default_web_searcher

            print(f"🌐 文件对话执行联网搜索: {query}")
            try:
                web_results = default_web_searcher.search(query, num_results=3)

                if web_results:
                    web_context = default_web_searcher.format_results_as_context(web_results)
                    context_parts.append(web_context)
                    print(f"✅ 搜索到 {len(web_results)} 个网络结果")
                else:
                    print("⚠️ 未搜索到网络结果")
            except Exception as e:
                print(f"❌ 网络搜索失败: {e}")

        # 6. 合并上下文
        context = "\n\n".join(context_parts) if context_parts else ""

        # 7. 调用LLM流式接口
        return self.llm_client.chat_completion(
            query=query,
            context=context,
            history=history,
            stream=True
        )

    def process_file_chat_stream(self, query: str, kb_id: str, file_id: str, use_kb: bool = False, use_net: bool = False):
        """
        处理文件级对话流式请求（包含历史获取和保存）

        Args:
            query: 用户查询
            kb_id: 知识库ID
            file_id: 文件ID
            use_kb: 是否使用知识库其他文件辅助
            use_net: 是否使用联网搜索

        Returns:
            流式响应生成器
        """
        # 1. 获取文件对话历史
        messages = self.conversation_manager.get_file_history(kb_id, file_id)

        # 2. 转换为字典格式（llm_client 期望的格式）
        history = []
        for msg in messages:
            # msg 是 HistoryMessage 对象，转换为字典
            if hasattr(msg, 'model_dump'):
                history.append(msg.model_dump())
            else:
                # 兼容旧格式，直接使用字典
                history.append(msg)

        print(f"📄 开始文件对话，历史消息数: {len(history)}，知识库辅助: {use_kb}，联网搜索: {use_net}")

        # 3. 调用文件对话流式方法
        response_stream = self._file_chat_stream(query, kb_id, file_id, use_kb, history, use_net)

        # 4. 流式输出并收集完整响应
        full_response = ""
        chunk_count = 0

        for chunk in response_stream:
            chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            full_response += chunk_content
            chunk_count += 1
            # print(f"🔧 文件对话生成 chunk {chunk_count}: {len(chunk_content)} 字符")
            yield chunk_content

        print(f"✅ 文件对话生成完成，共 {chunk_count} 个 chunk")

        # 5. 保存消息到文件对话历史
        self.conversation_manager.add_file_message(kb_id, file_id, query, 'user')
        self.conversation_manager.add_file_message(kb_id, file_id, full_response, 'ai')
    

    # ==================== 历史遗留产物 ====================

    # def get_conversation_history(self, paper_id: str = None) -> List[HistoryMessage]:
    #     """获取对话历史"""
    #     if paper_id:
    #         return self.conversation_manager.get_paper_history(paper_id)
    #     else:
    #         return self.conversation_manager.get_general_history()
    
    # def clear_conversation(self, paper_id: str = None) -> bool:
    #     """清除对话历史"""
    #     if paper_id:
    #         return self.conversation_manager.clear_paper_conversation(paper_id)
    #     else:
    #         self.conversation_manager.general_history.clear()
    #         return True

    
    # def process_query(self, request: ChatRequest) -> Dict:
    #     """
    #     处理查询（非流式）
    #     """
    #     begin_time = time.time()
        
    #     try:
    #         if request.deep:
    #             # 深度研究模式
    #             response_chunks = list(paper_survey(request.query))
    #             response = "".join(str(chunk) for chunk in response_chunks)
    #         else:
    #             # 普通聊天或论文问答
    #             if request.paper_id:
    #                 # 论文问答
    #                 history_objs = self.conversation_manager.get_paper_history(request.paper_id)
    #                 # 转换为字典格式
    #                 history = [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in history_objs]
    #                 response = self._paper_chat(request.query, history, request.paper_id)
    #             else:
    #                 # 通用聊天
    #                 history_objs = self.conversation_manager.get_general_history()
    #                 # 转换为字典格式
    #                 history = [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in history_objs]
    #                 response = self._general_chat(request.query, history, request.kb, request.net)
            
    #         # 保存对话历史
    #         if request.paper_id:
    #             self.conversation_manager.add_paper_message(request.paper_id, request.query, 'user')
    #             self.conversation_manager.add_paper_message(request.paper_id, response, 'ai')
    #         else:
    #             self.conversation_manager.add_general_message(request.query, 'user')
    #             self.conversation_manager.add_general_message(response, 'ai')
            
    #         end_time = time.time()
    #         process_time = end_time - begin_time
            
    #         return {
    #             "status": "success",
    #             "response": response,
    #             "processing_time": process_time,
    #             "query_length": len(request.query)
    #         }
            
    #     except Exception as e:
    #         return {
    #             "status": "error",
    #             "message": str(e)
    #         }
    
    # def process_query_stream(self, request: ChatRequest) -> Generator[str, None, None]:
    #     """
    #     处理查询（流式）
    #     """
    #     try:
    #         if request.deep:
    #             # 深度研究模式（流式）
    #             # 先提供开始信息
    #             start_info = "> 🚀 **任务已接收**：正在启动深度研究模式，准备拆解目标...\n\n"
    #             yield json.dumps({"chunk": start_info})
                
    #             from smolagents.memory import PlanningStep, ActionStep, FinalAnswerStep

    #             full_response = ""
    #             for chunk in paper_survey(request.query):
    #                 # 深度研究模式下，流式返回action step / final answer step
    #                 if isinstance(chunk, PlanningStep):
    #                     # 🧠 规划阶段：使用引用块 (>) + 粗体，表示这是思维过程
    #                     chunk_str = f"> 🧠 **深度规划**：已完成任务拆解，准备开始执行...\n\n"
                        
    #                 elif isinstance(chunk, ActionStep):
    #                     # 🛠️ 执行阶段：
    #                     # 1. 使用 #### 标题标记步骤
    #                     # 2. 将工具参数放在代码块 (```json) 中，利用前端的 Prism 高亮
    #                     tool_displays = []
                        
    #                     # 避免工具调用出错，导致没有记录toolcalls字段，直接从原始output中获取
    #                     if chunk.tool_calls is not None:
    #                         toolcalls = chunk.tool_calls
    #                     else:
    #                         toolcalls = [tc.function for tc in chunk.model_output_message.tool_calls]

    #                     if not toolcalls:
    #                         chunk_str = f"#### 📍 步骤 {chunk.step_number}\n- 正在执行...\n\n"
    #                     else:
    #                         for tc in toolcalls:
    #                             # 简单的参数展示优化
    #                             if tc.name == 'final_answer':
    #                                 tool_displays.append(f"- 正在生成最终答案...")
    #                                 continue
    #                             args_str = str(tc.arguments)
    #                             tool_displays.append(f"- 正在调用工具 **`{tc.name}`**...\n```json\n{args_str}\n```")
                            
    #                         toolcalls_info = '\n'.join(tool_displays)
    #                         chunk_str = f"#### 📍 步骤 {chunk.step_number}\n{toolcalls_info}\n\n"
                        
    #                 elif isinstance(chunk, FinalAnswerStep):
    #                     # 🏁 最终答案：
    #                     # 1. 先加一个分割线 (---) 把前面的思考过程隔开
    #                     # 2. 使用更大的标题 (###) 强调结果
    #                     chunk_str = f"\n\n---\n### 🎯 最终答案\n\n{chunk.output}\n"
    #                 elif isinstance(chunk, str):
    #                     # 这里先传个开始信息，提供情绪价值
    #                     chunk_str = chunk
                        
    #                 else:
    #                     chunk_str = ''

    #                 # chunk_str = str(chunk)
    #                 full_response += chunk_str
    #                 yield json.dumps({"chunk": chunk_str, "full_response": full_response})
                
    #             # 保存对话历史
    #             self.conversation_manager.add_general_message(request.query, 'user')
    #             self.conversation_manager.add_general_message(full_response, 'ai')
                
    #             # 发送完成信号
    #             yield json.dumps({"status": "complete", "full_response": full_response})
                
    #         else:
    #             # 普通聊天或论文问答（流式）
    #             # import pdb; pdb.set_trace()
    #             if request.paper_id:
    #                 # 论文问答
    #                 history_objs = self.conversation_manager.get_paper_history(request.paper_id)
    #                 # 转换为字典格式
    #                 history = [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in history_objs]
    #                 response_stream = self._paper_chat_stream(request.query, history, request.paper_id)
    #             else:
    #                 # 通用聊天
    #                 history_objs = self.conversation_manager.get_general_history()
    #                 # 转换为字典格式
    #                 history = [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in history_objs]
    #                 response_stream = self._general_chat_stream(request.query, history, request.kb, request.net)
                
    #             full_response = ""
                
    #             for chunk in response_stream:
    #                 chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
    #                 full_response += chunk_content
    #                 yield json.dumps({"chunk": chunk_content, "full_response": full_response})
                
    #             # 保存对话历史
    #             if request.paper_id:
    #                 self.conversation_manager.add_paper_message(request.paper_id, request.query, 'user')
    #                 self.conversation_manager.add_paper_message(request.paper_id, full_response, 'ai')
    #             else:
    #                 self.conversation_manager.add_general_message(request.query, 'user')
    #                 self.conversation_manager.add_general_message(full_response, 'ai')
                
    #             # 发送完成信号
    #             yield json.dumps({"status": "complete", "full_response": full_response})
                
    #     except Exception as e:
    #         yield json.dumps({"status": "error", "message": str(e)})

    # def _paper_chat(self, query: str, history: List[Dict], paper_id: str) -> str:
    #     """论文问答（非流式）"""
    #     # 使用基于论文ID的精确检索
    #     kb_result = self.kb_manager.search_by_paper_id(query=query, paper_id=paper_id, top_k=5)
        
    #     if not kb_result or not kb_result['documents'][0]:
    #         # 如果精确检索没有结果，回退到普通检索
    #         print("精确检索无结果，回退到普通检索")
    #         kb_result = self.kb_manager.search(query=query, mode="hybrid", top_k=3)
        
    #     context = ""
    #     if kb_result and kb_result['documents'][0]:
    #         metadatas = kb_result['metadatas'][0]
    #         docs = kb_result['documents'][0]
    #         kb_content = ''
    #         for i in range(len(docs)):
    #             kb_content += f"知识库内容 {i+1}：\n{docs[i]}\n来源论文：\n{metadatas[i]}\n"
    #         context = kb_content
        
    #     # 调用LLM（history 已经是字典格式）
    #     response = self.llm_client.chat_completion(
    #         query=query,
    #         context=context,
    #         history=history,
    #         stream=False
    #     )
        
    #     return response
    
    # def _paper_chat_stream(self, query: str, history: List[Dict], paper_id: str):
    #     """论文问答（流式）"""
    #     # 使用基于论文ID的精确检索
    #     kb_result = self.kb_manager.search_by_paper_id(query=query, paper_id=paper_id, top_k=5)
        
    #     if not kb_result or not kb_result['documents'][0]:
    #         # 如果精确检索没有结果，回退到普通检索
    #         print("精确检索无结果，回退到普通检索")
    #         kb_result = self.kb_manager.search(query=query, mode="hybrid", top_k=3)
        
    #     context = ""
    #     if kb_result and kb_result['documents'][0]:
    #         metadatas = kb_result['metadatas'][0]
    #         docs = kb_result['documents'][0]
    #         kb_content = ''
    #         for i in range(len(docs)):
    #             kb_content += f"知识库内容 {i+1}：\n{docs[i]}\n来源论文：\n{metadatas[i]}\n"
    #         print(kb_content)
    #         context = kb_content
        
    #     # 调用LLM流式接口（history 已经是字典格式）
    #     return self.llm_client.chat_completion(
    #         query=query,
    #         context=context,
    #         history=history,
    #         stream=True
    #     )

# 延迟初始化全局服务实例
chat_service = None

def get_chat_service(user_id: str = None):
    """获取聊天服务实例（延迟初始化）"""
    global chat_service
    if chat_service is None:
        chat_service = ChatService(user_id)
    return chat_service

def get_user_chat_service():
    """获取当前用户的聊天服务实例"""
    from app.core.user_context import UserContext
    user_id = UserContext.get_current_user_id()
    return ChatService(user_id)
