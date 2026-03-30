PAPER_EXTRACT_PROMPT = """
    你是一位享誉全球的计算机科学领域 **Senior Area Chair (资深领域主席)** 和 **审稿专家**。
    请基于以下从 PDF 解析出的论文全文（包含文本和结构化的图表数据），提取深度、精确的元数据。

    {structured_info}

    【输入数据说明】
    1. **正文内容**：论文的完整 OCR 文本。
    2. **特殊标记**：
    - `[Table Detected and Parsed]`: 此处插入了OCR识别并转为 Markdown 格式的表格数据。**这是提取 Performance Metrics 的最重要依据**，请务必分析表格中的 **SOTA 对比数据**。
    - `[Image Extracted]`: 表示此处有插图，请结合上下文文字理解图表含义。

    【输出 JSON Schema（必须严格遵循以下字段结构）】

    请按照以下 JSON 字段结构进行提取。如果文中未提及某项信息，请保持该字段为空（字符串为空串""，数字为0，布尔值为false）。

    {{
        "id": "",                                    // 论文ID（留空，外部填充）
        "title": "",                                // 论文标题
        "authors": "",                              // 作者列表（逗号分隔）
        "year": '0',                                // 发表年份（整数字符串）
        "abstract": "",                             // 摘要（200字以内中文，涵盖背景、方法、结果）
        "venue": "",                                // 发表会议或期刊（如 CVPR, NeurIPS, Nature, arXiv）
        "citation_count": "N/A",                    // 引用次数（如文中未提及则留空）
        "code_url": "",                             // GitHub代码链接
        "has_code": false,                          // 是否有代码（根据 code_url 自动判断）
        "tasks": "",                                // 核心任务（逗号分隔，如 "Object Detection, Instance Segmentation"）
        "methods": "",                              // 方法流派（逗号分隔，如 "Transformer, Diffusion Model"）
        "domains": "",                              // 应用领域（逗号分隔，如 "Autonomous Driving, Medical Imaging"）
        "datasets": "",                             // 数据集名称（逗号分隔，如 "ImageNet-1k, COCO 2017"）
        "problem": "",                              // 研究痛点/Research Gap（一句话概括）
        "contribution": "",                         // 核心创新点（分号分隔）
        "metrics": "",                              // 关键性能指标（分号分隔，必须包含数字和数据集名称）
        "ablation": "",                             // 消融实验发现（一句话）
        "limitations": "",                          // 局限性（分号分隔）
        "compute": "",                              // 计算资源（如 "Trained on 8x A100 GPUs"）
        "baselines": "",                            // 对比模型（分号分隔）
        "foundations": "",                          // 基础理论（分号分隔）
        "asset_images_count": 0,                    // 图片数量（留空，外部填充）
        "asset_tables_count": 0,                    // 表格数量（留空，外部填充）
        "image_paths": [],                          // 图片路径列表（留空，外部填充）
        "table_paths": [],                          // 表格路径列表（留空，外部填充）
        "summary": ""                               // 精简摘要（与 abstract 同义）
    }}

    【提取策略与思维链】

    1. **🕵️ 侦探模式：锁定身份 (基础信息)**
    - `title`: 准确提取论文标题。
    - `authors`: 提取所有作者姓名，用**逗号分隔**组成字符串。
    - `year`: 提取发表年份（整数）。
    - `venue`: 提取发表会议或期刊名称。
    - `citation_count`: 如果文首或元数据中直接展示了引用次数，请提取；否则留空或填 "N/A"。
    - `code_url`: 仔细扫描文中是否包含 **GitHub** 或其他开源代码链接。

    2. **🏷️ 语义标签**
    - `tasks`: 根据 Abstract 确定核心任务，用**逗号分隔**。
    - `domains`: 确定应用领域，用**逗号分隔**。
    - `methods`: 识别核心技术流派，用**逗号分隔**。
    - `datasets`: 扫描全文寻找实验部分提到的具体数据集名称，用**逗号分隔**。

    3. **🧠 逻辑挖掘：寻找核心价值**
    - `problem`: 在 Introduction 中寻找转折词 (如 "**However**", "**Despite**", "**Limitation**")。用**一句话**精准概括前人工作存在的具体缺陷 (Research Gap)。
    - `contribution`: 提取作者自述的核心贡献点，用**分号分隔**。
    - `metrics`: **这是关键字段**。扫描 `[Table Detected...]` 内容，提取关键性能指标，用**分号分隔**。
    - 格式示例："在 COCO 数据集上 mAP 达到 50.1% (比 Baseline 提升 +1.2%)"

    4. **⚖️ 专家批判：消融与局限**
    - `ablation`: 定位 "Ablation Study" 章节。用一句话总结消融实验的主要发现。
    - `limitations`: 去 Discussion 或 Conclusion 寻找作者自述的不足，用**分号分隔**。
    - `compute`: 寻找实验设置中提到的硬件资源。

    5. **🕸️ 知识图谱：建立连接**
    - `baselines`: 提取实验表格中作为主要对比对象的模型名称，用**分号分隔**。
    - `foundations`: 提取作者基于其改进的核心理论或架构名称，用**分号分隔**。

    6. **📝 总结**
    - `abstract`: 请用一段通顺的中文（200字以内），涵盖背景、核心方法、主要结果。
    - `summary`: 与 abstract 相同的内容。

    【输出要求】
    1. **语言风格**: 所有的描述性句子请使用 **中文**，但**专有名词**（如 Model Names, Dataset Names, Metric Names）必须保留 **英文原文**。
    2. **格式**: 严格遵循上述 JSON Schema 输出，由```json ...```包裹。
    3. **列表分隔**: 多个值请使用指定的分隔符（逗号或分号）连接成字符串。
    4. **空值处理**: 未提及的字段请填空值（字符串填 ""，数字填 0，布尔值填 false，列表填 []）。

    【论文全文内容】
    {content}
    """