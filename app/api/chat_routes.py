"""
聊天相关路由 - FastAPI版本
从Flask版本最小迁移
"""

import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.chat_service import get_chat_service
from app.services.conversation_service import get_conversation_service
from app.models.schemas import ChatRequest, ChatResponse, BaseResponse

router = APIRouter()


@router.post("/chat")
async def chat(request: Request):
    """非流式聊天接口 - 直接从Flask版本迁移"""
    try:
        # 验证请求数据
        data = await request.json()
        if not data or 'query' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400
        
        # 构建请求对象
        chat_request = ChatRequest(
            query=data['query'].strip(),
            net=data.get('net', False),
            kb=data.get('kb', False),
            deep=data.get('deep', False),
            paper_id=data.get('paper_id'),
            conversation_id=data.get('conversation_id')
        )
        
        if not chat_request.query:
            return BaseResponse(
                status="error",
                message="查询内容不能为空"
            ).model_dump(), 400
        
        # 获取聊天服务
        chat_service = get_chat_service()
        
        # 根据是否有conversation_id和paper_id决定处理方式
        if chat_request.paper_id:
            # 论文对话，使用原有逻辑（用完即弃）
            result = chat_service.process_query(chat_request)
        elif chat_request.conversation_id:
            # 在指定对话中处理查询
            result = chat_service.process_conversation_query(
                conversation_id=chat_request.conversation_id,
                query=chat_request.query
            )
        else:
            # 未指定conversation_id且不是论文对话，创建新对话
            create_result = chat_service.create_conversation()
            if create_result['status'] == 'success':
                new_conversation_id = create_result['conversation']['id']
                # 在新创建的对话中处理查询
                result = chat_service.process_conversation_query(
                    conversation_id=new_conversation_id,
                    query=chat_request.query
                )
                # 返回新创建的对话ID
                if result['status'] == 'success':
                    result['conversation_id'] = new_conversation_id
                    result['conversation'] = create_result['conversation']
            else:
                result = {
                    "status": "error",
                    "message": "创建新对话失败"
                }
        
        if result['status'] == 'success':
            # 如果提供了对话ID，将消息保存到指定对话中
            conversation_id = data.get('conversation_id')
            if conversation_id:
                conversation_manager = get_conversation_service()
                conversation_manager.add_message_to_conversation(
                    conversation_id, chat_request.query, 'user'
                )
                conversation_manager.add_message_to_conversation(
                    conversation_id, result['response'], 'assistant'
                )
            
            response = ChatResponse(
                status="success",
                response=result['response'],
                processing_time=result.get('processing_time'),
                query_length=result.get('query_length')
            )
            return response.model_dump()
        else:
            return BaseResponse(
                status="error",
                message=result.get('message', '处理失败')
            ).model_dump(), 500
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.post("/chat/stream")
async def chat_stream(request: Request):
    """流式聊天接口 - 直接从Flask版本迁移"""
    try:
        # 验证请求数据
        data = await request.json()
        if not data or 'query' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400
        
        # 构建请求对象
        chat_request = ChatRequest(
            query=data['query'].strip(),
            net=data.get('net', False),
            kb=data.get('kb', False),
            deep=data.get('deep', False),
            paper_id=data.get('paper_id')
        )
        
        if not chat_request.query:
            return BaseResponse(
                status="error",
                message="查询内容不能为空"
            ).model_dump(), 400
        
        # 获取对话ID（如果提供）
        conversation_id = data.get('conversation_id')
        
        def generate():
            try:
                # 获取流式响应
                chat_service = get_chat_service()
                response_stream = chat_service.process_query_stream(chat_request)
                
                full_response = ""
                # 流式输出
                for chunk in response_stream:
                    chunk_data = json.loads(chunk)
                    if 'chunk' in chunk_data:
                        full_response += chunk_data['chunk']
                    yield f"data: {chunk}\n\n"
                
                # 如果提供了对话ID，将消息保存到指定对话中
                if conversation_id:
                    conversation_manager = get_conversation_service()
                    conversation_manager.add_message_to_conversation(
                        conversation_id, chat_request.query, 'user'
                    )
                    conversation_manager.add_message_to_conversation(
                        conversation_id, full_response, 'assistant'
                    )
                
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        
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
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.get("/history")
async def get_history(request: Request):
    """获取对话历史"""
    try:
        from app.services.conversation_service import get_conversation_service
        
        paper_id = request.query_params.get('paper_id')
        
        history = get_conversation_service().get_conversation_history(paper_id)
        
        return {
            "status": "success",
            "history": [msg.model_dump() for msg in history]
        }
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"获取历史失败: {str(e)}"
        ).model_dump(), 500


@router.post("/history/clear")
async def clear_history(request: Request):
    """清除对话历史"""
    try:
        from app.services.conversation_service import get_conversation_service
        
        data = await request.json() or {}
        paper_id = data.get('paper_id')
        
        success = get_conversation_service().clear_conversation(paper_id)
        
        if success:
            return BaseResponse(
                status="success",
                message="对话历史已清除"
            ).model_dump()
        else:
            return BaseResponse(
                status="error",
                message="清除失败"
            ).model_dump(), 400
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"清除失败: {str(e)}"
        ).model_dump(), 500
    

@router.post("/conversations/{conversation_id}/stream")
async def chat_stream_in_conversation(conversation_id: str, request: Request):
    """流式聊天接口 - 在指定对话中"""
    try:
        # 验证请求数据
        data = await request.json()
        if not data or 'query' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400
        
        query = data['query'].strip()
        use_kb = data.get('kb', False)
        use_web = data.get('net', False)
        deep = data.get('deep', False)
        paper_id = data.get('paper_id')

        if not query:
            return BaseResponse(
                status="error",
                message="查询内容不能为空"
            ).model_dump(), 400
        
        def generate():
            try:
                from app.services.chat_service import get_chat_service
                
                chat_service = get_chat_service()
                
                # 使用新的对话流式方法
                response_stream = chat_service.process_conversation_query_stream(conversation_id, query, use_kb, use_web)
                
                # 流式输出
                for chunk in response_stream:
                    yield f"data: {chunk}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        
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
        
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500


@router.post("/chat/knowledge-base/stream")
async def chat_with_knowledge_base_stream(request: Request):
    """
    基于知识库的流式对话，支持指定文件和联网搜索

    请求参数：
        - query: 用户查询
        - kb_id: 知识库ID
        - kb_name: 知识库名称
        - file_ids: 文件ID列表（可选，为空则不使用知识库）
        - net: 是否使用联网搜索（可选，默认为 false）
    """
    try:
        # 验证请求数据
        data = await request.json()
        if not data or 'query' not in data:
            return BaseResponse(
                status="error",
                message="无效的请求"
            ).model_dump(), 400

        query = data['query'].strip()
        kb_id = data.get('kb_id')
        kb_name = data.get('kb_name', '')
        file_ids = data.get('file_ids', [])
        use_net = data.get('net', False)  # 新增：接收联网搜索参数

        if not query:
            return BaseResponse(
                status="error",
                message="查询内容不能为空"
            ).model_dump(), 400

        def generate():
            try:
                chat_service = get_chat_service()

                # 调用知识库对话流式方法（service 层会自动获取历史和保存消息）
                response_stream = chat_service.process_kb_chat_stream(
                    query=query,
                    kb_id=kb_id,
                    kb_name=kb_name,
                    file_ids=file_ids,
                    use_net=use_net  # 新增：传递联网搜索参数
                )

                full_response = ""
                chunk_count = 0

                # 流式输出
                for chunk in response_stream:
                    full_response += chunk
                    chunk_count += 1
                    # print(f"📤 发送 chunk {chunk_count}: {len(chunk)} 字符")
                    yield f"data: {json.dumps({'chunk': chunk, 'full_response': full_response})}\n"

                # 发送完成信号
                print(f"✅ 流式发送完成，共 {chunk_count} 个 chunk，总长度: {len(full_response)}")
                yield f"data: {json.dumps({'status': 'complete', 'full_response': full_response})}\n"

            except Exception as e:
                print(f"❌ 流式生成错误: {e}")
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

    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"服务器内部错误: {str(e)}"
        ).model_dump(), 500