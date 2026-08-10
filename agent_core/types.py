"""工作流数据模型（纯标准库，零第三方依赖）。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class TaskStep:
    """Planner 输出的单个任务步骤。"""

    id: int
    title: str
    description: str = ""
    step_type: str = "codegen"  # codegen | fileop | test | modify
    detail: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | running | success | failed | skipped
    result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    """任务规划结果。"""

    task: str
    steps: list[TaskStep] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "meta": self.meta,
        }


@dataclass
class GeneratedFile:
    """代码生成 Agent 产出的文件。"""

    path: str  # 相对工作区路径
    content: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    """工具调用结果。"""

    ok: bool
    output: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    """工作流事件（用于日志 / UI 流式展示）。"""

    stage: str
    agent: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewIssue:
    """代码审查发现的问题。"""

    severity: str  # critical | high | medium | low | info
    file: str
    title: str
    detail: str = ""
    suggestion: str = ""
    line: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewReport:
    """Reflection Agent 输出的代码审查报告。"""

    score: int
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "strengths": self.strengths,
            "suggestions": self.suggestions,
        }


@dataclass
class TestReport:
    """自动测试结果。"""

    ok: bool
    command: str = ""
    summary: str = ""
    output: str = ""
    checks: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowResult:
    """一次完整工作流的最终结果。"""

    requirement: str
    provider: str
    plan: TaskPlan
    events: list[Event] = field(default_factory=list)
    generated_files: list[GeneratedFile] = field(default_factory=list)
    test_report: Optional[TestReport] = None
    review_report: Optional[ReviewReport] = None
    workspace: str = ""
    fix_iterations: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement,
            "provider": self.provider,
            "plan": self.plan.to_dict() if self.plan else None,
            "events": [e.to_dict() for e in self.events],
            "generated_files": [f.to_dict() for f in self.generated_files],
            "test_report": self.test_report.to_dict() if self.test_report else None,
            "review_report": self.review_report.to_dict() if self.review_report else None,
            "workspace": self.workspace,
            "fix_iterations": self.fix_iterations,
            "error": self.error,
        }

