import os
from dataclasses import dataclass, fields
from typing import Any, Optional
from langchain_core.runnables import RunnableConfig
from dataclasses import dataclass

DEFAULT_REPORT_STRUCTURE = """
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


class Configuration:
    """配置字段"""
    report_structure: str = DEFAULT_REPORT_STRUCTURE
    max_search_queries: int = 5
    enable_web_search: bool = True

    @classmethod
    def from_runnable_config(
            cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """从RunnableConfig创建一个Configuration实例。"""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
