#!/usr/bin/env python3
"""
诊断脚本：检查 PDF 解析器配置
在服务器上运行此脚本验证代码是否正确
"""

import inspect
from app.core.pdf_parser import process_pdf_for_knowledge_base, process_pdf_with_unstructured

print("=" * 60)
print("PDF 解析器配置检查")
print("=" * 60)

# 检查函数默认参数
sig = inspect.signature(process_pdf_for_knowledge_base)
defaults = {k: v.default for k, v in sig.parameters.items() if v.default is not inspect.Parameter.empty}

print("\n📄 process_pdf_for_knowledge_base 默认参数:")
for k, v in defaults.items():
    print(f"   {k} = {v}")

# 检查 use_fast 是否为 True
if defaults.get('use_fast') == True:
    print("\n✅ use_fast=True (将使用 pypdfplumber 快速解析)")
else:
    print("\n❌ use_fast=False (将使用 PyMuPDF 慢速解析)")
    print("   请确保代码已更新并重启服务！")

# 检查 process_pdf_with_unstructured
sig2 = inspect.signature(process_pdf_with_unstructured)
defaults2 = {k: v.default for k, v in sig2.parameters.items() if v.default is not inspect.Parameter.empty}

print("\n📄 process_pdf_with_unstructured 默认参数:")
if defaults2.get('use_fast') == True:
    print("   use_fast = True ✅")
else:
    print("   use_fast = False ❌")

# 检查 pypdfplumber 是否可用
print("\n📦 依赖检查:")
try:
    import pdfplumber
    print("   pypdfplumber: ✅ 已安装")
except ImportError:
    print("   pypdfplumber: ❌ 未安装 (请运行: pip install pdfplumber)")

try:
    import fitz
    print("   PyMuPDF (fitz): ✅ 已安装")
except ImportError:
    print("   PyMuPDF (fitz): ❌ 未安装")

print("\n" + "=" * 60)
print("如果 use_fast 不为 True，请执行以下步骤:")
print("1. 确保代码已更新: git pull")
print("2. 清除缓存: find . -type d -name __pycache__ -exec rm -rf {} +")
print("3. 重启服务")
print("=" * 60)
