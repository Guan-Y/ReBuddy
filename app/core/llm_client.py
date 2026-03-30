"""LLM客户端封装"""
from smolagents import OpenAIServerModel
from smolagents.models import ChatMessage, MessageRole
import os
import dotenv
from app.config import Config

dotenv.load_dotenv(override=True)


class LLMClient:
    """LLM客户端，封装不同模型的调用"""
    
    def __init__(self, model_id=None, api_key=None, api_base=None, max_tokens=None):
        """初始化LLM客户端"""
        self.model_id = model_id or Config.MODEL_NAME
        self.api_key = api_key or Config.IFLOW_API_KEY
        self.api_base = api_base or Config.IFLOW_API_BASE
        self.max_tokens = max_tokens or Config.MAX_TOKENS
        
        # 初始化模型
        self.model = OpenAIServerModel(
            model_id=self.model_id,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            api_base=self.api_base
        )
    
    def generate(self, messages, system_prompt:str=None, **kwargs):
        """生成响应（非流式）"""
        if isinstance(messages, str):
            messages = [ChatMessage(role=MessageRole.USER, content=messages)]
        
        if system_prompt:
            system_message = ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
            messages = [system_message] + messages
    
        return self.model(messages)
    
    def generate_stream(self, messages, system_prompt:str=None, **kwargs):
        """生成响应（流式）"""
        if isinstance(messages, str):
            messages = [ChatMessage(role=MessageRole.USER, content=messages)]
        
        if system_prompt:
            system_message = ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
            messages = [system_message] + messages
    
        return self.model.generate_stream(messages)
    
    def chat_completion(self, query, context="", history=[], stream=False):
        """
        聊天完成接口
        Args:
            query: 用户查询
            context: 上下文信息
            history: 对话历史
            stream: 是否流式返回
        """
        # 构建对话历史
        conversation = []
        for msg in history:
            if msg['type'] == 'user':
                conversation.append(ChatMessage(role=MessageRole.USER, content=msg['content']))
            elif msg['type'] == 'ai':
                conversation.append(ChatMessage(role=MessageRole.ASSISTANT, content=msg['content']))
        
        # 构建当前查询
        if context:
            prompt = f"{query}\n\n请结合以下内容回答问题：\n{context}"
        else:
            prompt = query
        
        conversation.append(ChatMessage(role=MessageRole.USER, content=prompt))
        
        if stream:
            return self.generate_stream(conversation)
        else:
            response = self.generate(conversation)
            return response.content

    # ============ 异步接口 ============

    async def generate_async(self, messages, system_prompt: str = None, **kwargs):
        """
        异步生成响应（非流式）
        Args:
            messages: 消息列表或字符串
            system_prompt: 系统提示词
            **kwargs: 其他参数
        Returns:
            响应对象
        """
        import asyncio

        if isinstance(messages, str):
            messages = [ChatMessage(role=MessageRole.USER, content=messages)]

        if system_prompt:
            system_message = ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
            messages = [system_message] + messages

        # 在线程池中执行同步的模型调用
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.model, messages)

    async def generate_stream_async(self, messages, system_prompt: str = None, **kwargs):
        """
        异步生成响应（流式）
        Args:
            messages: 消息列表或字符串
            system_prompt: 系统提示词
            **kwargs: 其他参数
        Returns:
            流式响应生成器
        """
        import asyncio

        if isinstance(messages, str):
            messages = [ChatMessage(role=MessageRole.USER, content=messages)]

        if system_prompt:
            system_message = ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
            messages = [system_message] + messages

        # 在线程池中执行同步的流式调用
        loop = asyncio.get_event_loop()
        stream = await loop.run_in_executor(None, self.model.generate_stream, messages)

        # 将同步生成器转换为异步生成器
        async def async_generator():
            for chunk in stream:
                yield chunk

        return async_generator()

    async def chat_completion_async(self, query, context="", history=[], stream=False):
        """
        异步聊天完成接口
        Args:
            query: 用户查询
            context: 上下文信息
            history: 对话历史
            stream: 是否流式返回
        Returns:
            响应内容或流式生成器
        """
        # 构建对话历史
        conversation = []
        for msg in history:
            if msg['type'] == 'user':
                conversation.append(ChatMessage(role=MessageRole.USER, content=msg['content']))
            elif msg['type'] == 'ai':
                conversation.append(ChatMessage(role=MessageRole.ASSISTANT, content=msg['content']))

        # 构建当前查询
        if context:
            prompt = f"{query}\n\n请结合以下内容回答问题：\n{context}"
        else:
            prompt = query

        conversation.append(ChatMessage(role=MessageRole.USER, content=prompt))

        if stream:
            return await self.generate_stream_async(conversation)
        else:
            response = await self.generate_async(conversation)
            return response.content


# 预定义的客户端实例
default_client = LLMClient()