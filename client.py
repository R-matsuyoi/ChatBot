from Module import researcher
from Module import get_or_create_vector_db
from dotenv import load_dotenv

load_dotenv()

report_structure = """
# 报告摘要
- 简要概述报告的主要内容和结论，通常不超过 200 字

# 背景与目的
- 每个部分（1-5部分）：
  - 副标题：提供一个相关的副标题部分的关键方面.
  - 描述：对该部分讨论的概念或主题的详细解释.
  - 分析：用研究结果、统计数据、例子或案例研究来支持解释.

# 结论与建议
- 总结报告的主要发现和结论.
- 根据结论提出具体的、可操作的建议。

# 参考文献
- 列出报告中引用的所有文献资料，格式规范统一
"""

# 定义初始状态
initial_state = {
    "user_instructions": "介绍以deepseek为代表的大模型发展情况",
}

# Langgraph config
config = {
  "configurable": {
    "enable_web_search": True,
    "report_structure": report_structure,
    "max_search_queries": 5
}}

# 初始化向量数据库存储
# 必须先在/files目录下添加您自己的文档
vector_db = get_or_create_vector_db()

# Run the researcher graph
for output in researcher.stream(initial_state, config=config):
    for key, value in output.items():
        print(f"结束运行: **{key}**")
        print(value)

