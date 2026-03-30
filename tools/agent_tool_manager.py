from typing import Dict, List, Optional, Callable, Any, Union
from pydantic import BaseModel, Field, ValidationError
import json
import inspect
import logging
from abc import ABC, abstractmethod
import os
from smolagents import Tool
from smolagents import OpenAIServerModel, ZhipuAIServerModel
from smolagents.models import ChatMessage, MessageRole


# ==================== 数据模型定义 ====================
class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None

class ToolMetadata(BaseModel):
    """工具元数据，可作为工具经验库的基础"""
    name: str
    description: str
    parameters: Any
    tags: str=None
    version: str = "1.0.0"
    created_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())



# ==================== 核心管理类 ====================
class AgentToolManager:
    """Agent工具管理器"""
    
    def __init__(self, 
                 model: Optional[OpenAIServerModel] = None,
                 tools: Tool | List[Tool] = None
                 ):
        
        self.intro = "这是一个用于管理和操作各种工具的Agent工具管理器。当你需要使用某个工具时，可以通过本管理器进行注册、更新、创建和检索工具。"
        
        self.tools = {}
        self.tools_metadata = {}

        if tools:
            if not isinstance(tools, list):
                tools = [tools]

            for tool in tools:
                self.tools[tool.name] = tool
                metadata = ToolMetadata(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputs
                    )
                self.tools_metadata[tool.name] = metadata


        default_model_params = {
            'model_id': "glm-4.5-air",
            'max_tokens': 4096,
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_API_BASE"),
        }
        
        self.model = model or \
            ZhipuAIServerModel(**default_model_params)
        
        self.logger = logging.getLogger(__name__)

        self.code_executor = None  # 可选的代码执行环境
        
        # 系统提示词
        self.tool_creation_prompt = """
        你是一个工具创建助手。请根据用户的需求，生成一个符合以下JSON格式的工具定义：
        {
            "name": "工具名称（英文，snake_case）",
            "description": "清晰描述工具功能的文本",
            "parameters": [
                {
                    "name": "参数名",
                    "type": "参数类型（str, int, float, bool, list, dict）",
                    "description": "参数说明",
                    "required": true/false
                }
            ],
            "return_value": {
                "type": "返回值类型",
                "description": "返回值说明"
            },
            "code_template": "Python函数代码模板"
        }
        
        要求：
        1. 参数必须明确、完整
        2. 包含类型注解
        3. 有清晰的文档字符串
        4. 包含基本的输入验证
        """
    
    # ==================== 1. 工具注册 ====================
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: List[Dict[str, Any]],
        func: Callable,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
        validate: bool = True
    ) -> None:
        """注册新工具"""
        try:
            # 参数转换
            tool_params = [
                ToolParameter(**param) if isinstance(param, dict) else param
                for param in parameters
            ]
            
            # 创建元数据
            metadata = ToolMetadata(
                name=name,
                description=description,
                parameters=tool_params,
                func=func,
                tags=tags or [],
                version=version
            )
            
            # 验证唯一性
            if validate and name in self.tools:
                raise ValueError(f"工具 '{name}' 已存在，请使用 update_tool 更新或先删除")
            
            self.tools[name] = metadata
            self.logger.info(f"工具注册成功: {name} v{version}")
            
        except ValidationError as e:
            self.logger.error(f"工具元数据验证失败: {e}")
            raise
    
    # ==================== 2. 工具更新 ====================
    def update_tool(
        self,
        name: str,
        description: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        func: Optional[Callable] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None
    ) -> None:
        """更新现有工具"""
        if name not in self.tools:
            raise KeyError(f"工具 '{name}' 不存在")
        
        pass

        self.logger.info(f"工具更新成功: {name}")
    
    # ==================== 3. 工具创建 ====================
    def create_tool(
        self,
        requirement: str,
        auto_implement: bool = False,
        code_template: Optional[str] = None
    ) -> Union[Dict[str, Any], Callable]:
        """
        通过LLM创建工具定义或实现
        Args:
            requirement: 工具需求描述
            auto_implement: 是否自动生成可执行代码
            code_template: 可选的代码模板
        """
        if not self.model:
            raise RuntimeError("未配置LLM提供商，无法创建工具")
        
        prompt = f"""
        {self.tool_creation_prompt}
        
        用户需求: {requirement}
        """
        
        if code_template:
            prompt += f"\n代码模板: {code_template}"
        
        try:
            response = self.model(
                prompt=prompt,
                system_message="你是一个专业的Python工具创建助手",
                temperature=0.3
            )
            
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("LLM返回结果中未找到有效的JSON格式")
            
            tool_def = json.loads(json_match.group())
            
            if auto_implement:
                # 动态执行生成的代码
                exec_globals = {}
                exec(tool_def['code_template'], exec_globals)
                func = exec_globals.get(tool_def['name'])
                
                if not func:
                    raise RuntimeError("代码生成成功但无法提取函数")
                
                # 自动注册
                self.register_tool(
                    name=tool_def['name'],
                    description=tool_def['description'],
                    parameters=tool_def['parameters'],
                    func=func
                )
                
                return func
            
            return tool_def
            
        except Exception as e:
            self.logger.error(f"工具创建失败: {e}")
            raise
    
    # ==================== 4. 工具合并 ====================
    def merge_tools(
        self,
        source_tools: Dict[str, ToolMetadata],
        target_name: str,
        merge_strategy: str = "override",
        prefix: Optional[str] = None
    ) -> None:
        """
        合并工具集合
        
        Args:
            source_tools: 源工具字典
            target_name: 目标工具集名称（用于命名空间）
            merge_strategy: 合并策略 (override/ignore/skip)
            prefix: 可选的工具名前缀
        """
        for tool_name, metadata in source_tools.items():
            final_name = f"{prefix}_{tool_name}" if prefix else tool_name
            
            if final_name in self.tools:
                if merge_strategy == "override":
                    self.tools[final_name] = metadata
                    self.logger.info(f"覆盖工具: {final_name}")
                elif merge_strategy == "ignore":
                    self.logger.info(f"忽略已存在工具: {final_name}")
                elif merge_strategy == "skip":
                    continue
            else:
                self.tools[final_name] = metadata
                self.logger.info(f"添加新工具: {final_name}")
        
        self.logger.info(f"工具合并完成: {target_name}")
    
    # ==================== 5. 工具检索 ====================
    def retrieve_tool(
        self,
        query: str = None,
        max_returns: int = 3,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        fuzzy: bool = False
    ) -> List[ToolMetadata]:
        """检索工具，支持多种查询方式"""
        results = []

        if query:
            all_tools = self.list_tools()
            tools_content = "Available Tools:\n"
            for _, tool in all_tools.items():
                tools_content += f"- Name: {tool['name']}\n  Description: {tool['description']}\n  Args: {tool['parameters']}\n"
            
            prompt = f"User's query:{query}\nPlease identify the most relevant tools from the following list:\n{tools_content}\nRespond with the tool name. Return at most {max_returns} tools"

            input_messages = [ChatMessage(role=MessageRole.USER, content=prompt)]
            response = self.model(input_messages)
            # 这里应该解析响应，然后根据name返回完整的工具信息和调用方式给agent

            return response.content.strip()

        # 按名称精确查找
        if name:
            if name in self.tools:
                results.append(self.tools[name])
            elif not fuzzy:
                return results
        
        # 按标签查找
        if tag:
            results.extend([
                tool for tool_name, tool in self.tools.items()
                if tag in tool.tags and (not name or tool_name != name)
            ])
        
        # 按关键词模糊查找
        if keyword:
            keyword_lower = keyword.lower()
            for tool_name, tool in self.tools.items():
                if (fuzzy and keyword_lower in tool_name.lower()) or \
                   keyword_lower in tool.description.lower():
                    if tool not in results:
                        results.append(tool)
        
        return results
    
    # ==================== 辅助方法 ====================
    def delete_tool(self, name: str) -> bool:
        """删除工具"""
        if name in self.tools:
            del self.tools[name]
            self.logger.info(f"工具删除成功: {name}")
            return True
        return False
    
    def list_tools(self) -> Dict[str, dict]:
        """列出所有工具（序列化格式）"""
        return {
            name: tool.model_dump()
            for name, tool in self.tools_metadata.items()
        }
    
    def execute_tool(self, name: str, **kwargs) -> Any:
        """执行工具函数"""
        if name not in self.tools:
            raise KeyError(f"工具 '{name}' 不存在")
        
        tool = self.tools[name]
        
        # 参数验证
        for param in tool.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"缺少必需参数: {param.name}")
        
        return tool.func(**kwargs)
    
    def get_tool_schema(self, name: str) -> dict:
        """获取工具JSON Schema"""
        if name not in self.tools:
            raise KeyError(f"工具 '{name}' 不存在")
        
        tool = self.tools[name]
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: {
                            "type": param.type,
                            "description": param.description,
                            "default": param.default
                        }
                        for param in tool.parameters
                    },
                    "required": [
                        param.name for param in tool.parameters if param.required
                    ]
                }
            }
        }

# smolagents工具兼容版
class ToolRequest(Tool):
    name = "tool_request"
    description = """Based on the user's natural-language request, intelligently match and return the most appropriate tool."""
 
    inputs = {
        "query": {
            "type": "string", 
            "description": """
A detailed description of the required tool's functionality, for example:
"I need a tool that can search Python code on GitHub."
"Help me find a tool that can check real-time weather information."
"I'm looking to do data visualization—recommend a suitable tool."
"""
        }
    }
    output_type = "string"

    def __init__(self, toolmanager=None):
        super().__init__()
        self.manager = toolmanager

    def forward(self, query: str) -> str:
        NotImplemented
    
# MCP版：待开发


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    from .text_web_browser import (
        ArchiveSearchTool,
        FinderTool,
        FindNextTool,
        PageDownTool,
        PageUpTool,
        SimpleTextBrowser,
        VisitTool,
    )

    browser = None

    WEB_TOOLS = [
        VisitTool(browser),
        PageUpTool(browser),
        PageDownTool(browser),
        FinderTool(browser),
        FindNextTool(browser),
        ArchiveSearchTool(browser),
    ]

    # 1. 初始化（可选LLM）
    # manager = AgentToolManager(model=OpenAIProvider(api_key="your-key"))
    manager = AgentToolManager(tools=WEB_TOOLS)
    goodtools = manager.retrieve_tool(query="I need a tool to browse web pages and find information about recent technology trends.")

    import pdb; pdb.set_trace()
    
    # 2. 手动注册工具
    def calculator(a: int, b: int, operation: str = "add") -> float:
        """计算器工具"""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("除数不能为零")
            return a / b
        else:
            raise ValueError(f"不支持的操作: {operation}")
    
    manager.register_tool(
        name="calculator",
        description="执行基本数学运算",
        parameters=[
            {"name": "a", "type": "int", "description": "第一个操作数", "required": True},
            {"name": "b", "type": "int", "description": "第二个操作数", "required": True},
            {"name": "operation", "type": "str", "description": "操作类型", "required": False, "default": "add"}
        ],
        func=calculator,
        tags=["math", "utility"]
    )
    
    # 3. 检索工具
    math_tools = manager.retrieve_tool(tag="math")
    print(f"找到 {len(math_tools)} 个数学工具")
    
    # 4. 执行工具
    result = manager.execute_tool("calculator", a=10, b=5, operation="multiply")
    print(f"计算结果: {result}")
    
    # 5. 获取Schema（用于OpenAI Function Calling）
    schema = manager.get_tool_schema("calculator")
    print(json.dumps(schema, indent=2))
    
    # 6. LLM创建工具（需要配置API Key）
    # new_tool_def = manager.create_tool("创建一个获取当前天气的工具")
    # print(new_tool_def)