"""
深度研究核心模块 - 从原searcher.py迁移并重构
去除Flask依赖，保持纯算法逻辑
"""

from smolagents import ToolCallingAgent
from mcp import StdioServerParameters
from smolagents.tools import ToolCollection
import os

from app.core.llm_client import LLMClient
from app.config import Config


class DeepResearcher:
    """深度研究工具"""
    
    def __init__(self, llm_client: LLMClient = None):
        """初始化深度研究器"""
        self.llm_client = llm_client or LLMClient()
        
        # 浏览器工具配置
        self._setup_browser_tools()
        
        # MCP服务器配置
        self._setup_mcp_servers()
    
    def _setup_browser_tools(self):
        """设置浏览器工具"""
        from tools.text_web_browser import (
            ArchiveSearchTool,
            FinderTool,
            FindNextTool,
            PageDownTool,
            PageUpTool,
            SimpleTextBrowser,
            VisitTool,
        )
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        browser_config = {
            "viewport_size": Config.BROWSER_VIEWPORT_SIZE,
            "downloads_folder": "downloads_folder",
            "request_kwargs": {
                "headers": {"User-Agent": user_agent},
                "timeout": Config.BROWSER_TIMEOUT,
            },
            "serpapi_key": Config.SERPAPI_API_KEY,
        }
        
        os.makedirs(f"./{browser_config['downloads_folder']}", exist_ok=True)
        
        browser = SimpleTextBrowser(**browser_config)
        
        self.web_tools = [
            VisitTool(browser),
            PageUpTool(browser),
            PageDownTool(browser),
            FinderTool(browser),
            FindNextTool(browser),
            ArchiveSearchTool(browser),
        ]
    
    def _setup_mcp_servers(self):
        """设置MCP服务器"""
        self.mcp_servers = {
            "arxiv-mcp-server": {
                "command": "uv",
                "args": [
                    "--directory",
                    "./arxiv-mcp-server",
                    "run",
                    "arxiv-mcp-server",
                    "--storage-path", "./arxiv"
                ]
            }
        }
    
    def research(self, query: str, max_steps: int = 8):
        """
        执行深度研究
        Args:
            query: 研究查询
            max_steps: 最大步数
        Returns:
            生成器，产生研究步骤和结果
        """
        # 设置Arxiv MCP Server
        serverparams = StdioServerParameters(
            command=self.mcp_servers['arxiv-mcp-server']['command'],
            args=self.mcp_servers['arxiv-mcp-server']['args']
        )
        
        # 创建工具集合
        cm = ToolCollection.from_mcp(serverparams, trust_remote_code=True)
        tool_collection = cm.__enter__()
        
        try:
            # 创建代理
            agent = ToolCallingAgent(
                tools=tool_collection.tools + self.web_tools,
                model=self.llm_client.model,
                max_steps=max_steps,
                planning_interval=None
            )
            
            # 执行研究
            stream = agent.run(task=query, stream=True)
            for chunk in stream:
                yield chunk
                
        finally:
            # 清理资源
            cm.__exit__(None, None, None)
        
        yield "任务完成"


# 全局实例
default_researcher = DeepResearcher()


def paper_survey(query: str):
    """
    论文调研接口（保持与原函数兼容）
    """
    return default_researcher.research(query)


# ==================== 网络搜索器 ====================

class WebSearcher:
    """网络搜索器（轻量级）"""

    def __init__(self, serpapi_key: str = None, tavily_api_key: str = None):
        """初始化搜索器"""
        from app.config import Config

        self.serpapi_key = serpapi_key or Config.SERPAPI_API_KEY
        self.tavily_api_key = tavily_api_key or Config.TAVILY_SEARCH_API_KEY
        self.browser = None
        self.search_engine = "auto"  # auto, serpapi, tavily

        # 优先使用 Tavily
        if self.tavily_api_key:
            self.search_engine = "tavily"
            print("✅ 使用 Tavily 搜索引擎")
        elif self.serpapi_key:
            self.search_engine = "serpapi"
            # self._init_browser()
            print("✅ 使用 SerpAPI 搜索引擎")
        else:
            print("⚠️ 未配置搜索 API Key（SERPAPI_API_KEY 或 TAVILY_SEARCH_API_KEY），网络搜索功能将不可用")

    def search(self, query: str, num_results: int = 5) -> list:
        """
        执行网络搜索（自动选择搜索引擎）

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            搜索结果列表，每个结果包含：
            - title: 标题
            - link: 链接
            - snippet: 摘要
        """
        # 根据配置的搜索引擎自动选择
        if self.search_engine == "tavily":
            return self.tavily_search(query, num_results)
        elif self.search_engine == "serpapi":
            if not self.browser:
                print("⚠️ 搜索器未初始化（缺少 SERPAPI_API_KEY）")
                return []

            try:
                # 使用 Google 搜索
                search_query = f"google:{query}"
                self.browser.set_address(search_query)

                # 解析搜索结果
                results = self._parse_search_results(self.browser.page_content)

                # 限制返回数量
                return results[:num_results]

            except Exception as e:
                print(f"❌ 网络搜索失败: {e}")
                return []
        else:
            print("⚠️ 未配置搜索引擎")
            return []

    def _parse_search_results(self, content: str) -> list:
        """
        解析搜索结果页面

        Args:
            content: 页面内容

        Returns:
            搜索结果列表
        """
        results = []

        # 简单解析：查找搜索结果模式
        # 格式：[标题](链接) - 摘要
        import re

        # 匹配模式：[标题](链接) 摘要
        pattern = r'\[([^\]]+)\]\(([^)]+)\)\s*-\s*([^\n]+)'
        matches = re.findall(pattern, content)

        for title, link, snippet in matches:
            results.append({
                'title': title.strip(),
                'link': link.strip(),
                'snippet': snippet.strip()
            })

        # 如果没有匹配到，尝试其他模式
        if not results:
            # 备用模式：简单的文本行解析
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'http' in line and line.strip():
                    # 尝试提取标题和链接
                    parts = line.split('http')
                    if len(parts) > 1:
                        title = parts[0].strip()
                        link = 'http' + parts[1].split()[0].strip()
                        snippet = ' '.join(parts[1].split()[1:]).strip()
                        if title and link:
                            results.append({
                                'title': title,
                                'link': link,
                                'snippet': snippet
                            })

        return results

    def format_results_as_context(self, results: list) -> str:
        """
        将搜索结果格式化为上下文文本

        Args:
            results: 搜索结果列表

        Returns:
            格式化的上下文文本
        """
        if not results:
            return ""

        context = "【网络搜索结果】\n"
        for i, result in enumerate(results, 1):
            context += f"\n{i}. {result['title']}\n"
            context += f"   链接: {result['link']}\n"
            context += f"   摘要: {result['snippet']}\n"

        return context

    def tavily_search(self, query: str, num_results: int = 5) -> list:
        """
        使用 Tavily API 执行搜索

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            搜索结果列表，每个结果包含：
            - title: 标题
            - link: 链接
            - snippet: 摘要
        """
        if not self.tavily_api_key:
            print("⚠️ 未配置 TAVILY_SEARCH_API_KEY")
            return []

        try:
            from tavily import TavilyClient

            # 创建 Tavily 客户端
            client = TavilyClient(self.tavily_api_key)

            print(f"🔍 使用 Tavily 搜索: {query}")

            # 执行搜索
            response = client.search(
                query=query,
                max_results=num_results,
                search_depth="basic",
                include_answer=False,
                include_raw_content=False,
                include_images=False,
            )

            # 解析结果
            results = []
            if "results" in response:
                for item in response["results"]:
                    results.append({
                        'title': item.get('title', ''),
                        'link': item.get('url', ''),
                        'snippet': item.get('content', '')
                    })

            print(f"✅ Tavily 搜索完成，找到 {len(results)} 个结果")
            return results

        except Exception as e:
            print(f"❌ Tavily 搜索失败: {e}")
            return []


# 全局实例
default_web_searcher = WebSearcher()