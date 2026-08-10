"""AI Coding Agent Demo 核心引擎。

模拟真实 AI 软件工程师工作流：
需求理解 -> 任务规划 -> 文件分析 -> 代码生成 -> 自动修改 -> 测试验证 -> 结果优化。
"""

from .orchestrator import AgentWorkflow, WorkflowResult
from .llm import (
    BaseLLMProvider,
    MockProvider,
    OpenAIProvider,
    QwenProvider,
    create_provider,
    extract_json,
)

__all__ = [
    "AgentWorkflow",
    "WorkflowResult",
    "BaseLLMProvider",
    "MockProvider",
    "OpenAIProvider",
    "QwenProvider",
    "create_provider",
    "extract_json",
]

__version__ = "0.1.0"

