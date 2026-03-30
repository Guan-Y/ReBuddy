# Knowledge Base Search Tool

基于 smolagents 框架设计的知识库搜索工具，支持摘要搜索和全文搜索。

## 功能特性

- **三种搜索模式**：
  - `summary`: 搜索论文摘要，适合快速了解论文概览
  - `detail`: 搜索全文片段，适合查找具体细节
  - `hybrid`: 混合搜索，同时搜索摘要和全文（默认）

- **灵活的过滤**：
  - 支持按知识库 ID 过滤
  - 支持按用户 ID 个性化搜索

- **智能结果格式化**：
  - 自动格式化搜索结果
  - 支持结果摘要生成（需要 LLM 模型）

## 使用方法

### 基本使用

```python
from app.core.tools import KnowledgeBaseSearchTool

# 初始化工具
search_tool = KnowledgeBaseSearchTool()

# 执行搜索
results = search_tool.forward(
    query="transformer architecture",
    mode="summary",
    top_k=3
)

print(results)
```

### 使用 LLM 模型生成摘要

```python
from smolagents.models import Model
from app.core.tools import KnowledgeBaseSearchTool

# 初始化工具和模型
model = Model()  # 配置你的 LLM 模型
search_tool = KnowledgeBaseSearchTool(model=model)

# 执行搜索并生成摘要
results = search_tool.forward(
    query="object detection methods",
    mode="hybrid",
    top_k=5
)

print(results)
```

### 在 smolagents Agent 中使用

```python
from smolagents import CodeAgent
from app.core.tools import KnowledgeBaseSearchTool

# 创建 agent 并添加工具
agent = CodeAgent(tools=[KnowledgeBaseSearchTool()])

# 使用 agent 搜索
agent.run("Find papers about transformer architecture and summarize their key contributions")
```

## 参数说明

### 输入参数

- `query` (string, 必需): 搜索查询，使用自然语言描述
- `mode` (string, 可选): 搜索模式
  - `"summary"`: 摘要搜索
  - `"detail"`: 全文搜索
  - `"hybrid"`: 混合搜索（默认）
- `top_k` (integer, 可选): 返回结果数量（默认: 3，最大: 10）
- `user_id` (string, 可选): 用户 ID，用于个性化搜索
- `kb_id` (string, 可选): 知识库 ID，用于限定搜索范围

### 输出

返回格式化的搜索结果字符串，包含：
- 搜索模式信息
- 每个结果的元数据（标题、作者、年份等）
- 搜索内容
- 可选的 LLM 生成的摘要

## 示例查询

### 摘要搜索
```python
search_tool.forward(
    query="Find papers about attention mechanism",
    mode="summary",
    top_k=5
)
```

### 全文搜索
```python
search_tool.forward(
    query="What is the exact accuracy reported in the paper?",
    mode="detail",
    top_k=3
)
```

### 混合搜索
```python
search_tool.forward(
    query="Compare different approaches to image classification",
    mode="hybrid",
    top_k=5
)
```

### 限定知识库搜索
```python
search_tool.forward(
    query="machine learning techniques",
    mode="summary",
    top_k=3,
    kb_id="my_kb_id"
)
```

## 技术细节

### 依赖

- `smolagents`: Agent 框架
- `app.core.kb_manager`: 知识库管理器
- `qdrant-client`: 向量数据库客户端（可选）

### 初始化

工具使用懒加载初始化，首次调用时会自动初始化知识库管理器。

### 错误处理

- 空查询：返回错误提示
- 无效模式：自动回退到 `hybrid` 模式
- 超出最大结果数：自动限制到最大值
- 知识库未初始化：返回错误提示

## 扩展

### 自定义最大结果数

```python
search_tool = KnowledgeBaseSearchTool(max_results=20)
```

### 自定义 LLM 模型

```python
from smolagents.models import Model

custom_model = Model(
    model_id="your-model-id",
    # 其他配置...
)
search_tool = KnowledgeBaseSearchTool(model=custom_model)
```

## 注意事项

1. 确保知识库已正确初始化并包含数据
2. 搜索查询越具体，结果越准确
3. 使用 `summary` 模式可以快速浏览相关论文
4. 使用 `detail` 模式可以查找具体信息
5. 使用 `hybrid` 模式可以获得最全面的结果
6. 结果数量越多，响应时间越长