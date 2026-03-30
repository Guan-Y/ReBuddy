from smolagents import ZhipuAIServerModel, ToolCallingAgent
from smolagents.models import ChatMessage, MessageRole
import os
import dotenv

from mcp import StdioServerParameters
from smolagents import CodeAgent,OpenAIServerModel  # type: ignore
from smolagents.tools import ToolCollection


dotenv.load_dotenv(override=True)

model_params = {
    'model_id': "glm-4.5-air",
    'max_tokens': 4096,
    "api_key": os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("OPENAI_API_BASE"),
}

model = ZhipuAIServerModel(**model_params)

tools = []

agent = ToolCallingAgent(
    tools=[],
    model=model,
    max_steps=4,
    planning_interval=2
)

query = "告诉我A股和美股的区别"

input_messages = [ChatMessage(role=MessageRole.USER, content=query)]

import pdb; pdb.set_trace()
response = model(input_messages)

result = agent.run(task=query)

print(result)


#  Arxiv MCP Server Configuration Example
# {
#     "mcpServers": {
#         "arxiv-mcp-server": {
#             "command": "uv",
#             "args": [
#                 "tool",
#                 "run",
#                 "arxiv-mcp-server",
#                 "--storage-path", "/path/to/paper/storage"
#             ]
#         }
#     }
# }