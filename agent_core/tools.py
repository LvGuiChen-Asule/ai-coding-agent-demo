"""Tool Calling 工具注册系统。

模仿 OpenAI Function Calling / MCP Tool 概念：
Agent 根据任务自主选择工具，工具统一注册、统一调用、统一记录。
"""

from __future__ import annotations

import difflib
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .types import ToolResult


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Tool:
    """工具定义。"""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., ToolResult]

    def call(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            result = self.handler(**arguments)
            return result if isinstance(result, ToolResult) else ToolResult(ok=True, output=str(result))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, error=str(exc))


class ToolRegistry:
    """工具注册表：注册、列出、调用。"""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self._tools: dict[str, Tool] = {}
        self.call_log: list[dict[str, Any]] = []

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._tools.values()
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"未知工具: {name}")
        started = time.time()
        result = tool.call(arguments)
        self.call_log.append(
            {
                "ts": _now(),
                "tool": name,
                "arguments": arguments,
                "ok": result.ok,
                "error": result.error,
                "cost_ms": int((time.time() - started) * 1000),
            }
        )
        return result

    # ------------------------------------------------------------------
    # 内置工具

    def _safe_path(self, rel_path: str) -> Path:
        path = (self.workspace / rel_path).resolve()
        root = self.workspace.resolve()
        if not str(path).startswith(str(root)):
            raise PermissionError(f"路径超出工作区，已拒绝: {rel_path}")
        return path

    def file_reader(self, path: str, with_lines: bool = False) -> ToolResult:
        """FileReader：读取代码文件。"""
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(ok=False, error=f"文件不存在: {path}")
        content = target.read_text(encoding="utf-8", errors="replace")
        if with_lines:
            lines = content.splitlines()
            width = len(str(len(lines)))
            content = "\n".join(f"{i + 1:>{width}} | {line}" for i, line in enumerate(lines))
        return ToolResult(ok=True, output=content, data={"path": path, "size": len(content)})

    def list_dir(self, path: str = ".") -> ToolResult:
        """FileReader：列出目录。"""
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(ok=False, error=f"目录不存在: {path}")
        items = [
            {"name": p.name, "type": "dir" if p.is_dir() else "file", "size": p.stat().st_size}
            for p in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        ]
        return ToolResult(ok=True, output="\n".join(i["name"] for i in items), data={"items": items})

    def file_writer(self, path: str, content: str, reason: str = "") -> ToolResult:
        """FileWriter：写文件。自动备份原文件并记录 diff。"""
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        diff_text = ""
        if target.exists():
            before = target.read_text(encoding="utf-8", errors="replace")
            diff_text = "".join(
                difflib.unified_diff(
                    before.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
            )
            backup_dir = self.workspace / ".agent_backups"
            backup_dir.mkdir(exist_ok=True)
            backup = backup_dir / f"{target.name}.{int(time.time())}.bak"
            shutil.copy2(target, backup)
        else:
            diff_text = f"新增文件: {path} ({len(content)} 字符)\n"

        target.write_text(content, encoding="utf-8")
        return ToolResult(
            ok=True,
            output=f"已写入 {path}" + (f"\n{diff_text}" if diff_text else ""),
            data={"path": path, "diff": diff_text, "reason": reason},
        )

    def terminal(self, command: str, cwd: str = ".", timeout: int = 120) -> ToolResult:
        """Terminal：执行命令（限工作区内目录）。"""
        workdir = self._safe_path(cwd)
        if not workdir.exists():
            return ToolResult(ok=False, error=f"目录不存在: {cwd}")
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, error=f"命令超时（>{timeout}s）: {command}")
        output = (proc.stdout or "") + (proc.stderr or "")
        return ToolResult(
            ok=proc.returncode == 0,
            output=output.strip()[:4000],
            data={"command": command, "exit_code": proc.returncode},
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
        )

    def git(self, args: str, cwd: str = ".") -> ToolResult:
        """Git：版本管理。"""
        workdir = self._safe_path(cwd)
        return self.terminal(f"git {args}", cwd=str(workdir.relative_to(self.workspace)))

    def test_runner(self, cwd: str = ".") -> ToolResult:
        """TestRunner：自动检测并运行测试。"""
        workdir = self._safe_path(cwd)
        if (workdir / "mvnw").exists() or shutil.which("mvn"):
            return self.terminal("mvn test", cwd=str(workdir.relative_to(self.workspace)), timeout=300)
        if (workdir / "package.json").exists():
            return self.terminal("npm test", cwd=str(workdir.relative_to(self.workspace)), timeout=180)
        py_files = list(workdir.rglob("test_*.py")) + list(workdir.rglob("*_test.py"))
        if py_files:
            return self.terminal(
                "python -m unittest discover -s .",
                cwd=str(workdir.relative_to(self.workspace)),
                timeout=180,
            )
        return ToolResult(ok=False, error="未检测到可运行的测试框架（mvn / npm / python unittest）")


def build_registry(workspace: Path) -> ToolRegistry:
    """构建带全部内置工具的注册表。"""
    registry = ToolRegistry(workspace)
    registry.register(
        Tool(
            name="FileReader",
            description="读取代码文件内容，支持行号输出",
            parameters={"path": {"type": "string"}, "with_lines": {"type": "boolean", "default": False}},
            handler=registry.file_reader,
        )
    )
    registry.register(
        Tool(
            name="FileWriter",
            description="创建 / 修改文件，自动备份并生成 diff",
            parameters={
                "path": {"type": "string"},
                "content": {"type": "string"},
                "reason": {"type": "string", "default": ""},
            },
            handler=registry.file_writer,
        )
    )
    registry.register(
        Tool(
            name="Terminal",
            description="在工作区内执行命令（如 mvn test / python）",
            parameters={"command": {"type": "string"}, "cwd": {"type": "string", "default": "."}},
            handler=registry.terminal,
        )
    )
    registry.register(
        Tool(
            name="Git",
            description="Git 版本管理（status / add / commit / log）",
            parameters={"args": {"type": "string"}, "cwd": {"type": "string", "default": "."}},
            handler=registry.git,
        )
    )
    registry.register(
        Tool(
            name="TestRunner",
            description="自动检测并运行测试（Maven / npm / Python unittest）",
            parameters={"cwd": {"type": "string", "default": "."}},
            handler=registry.test_runner,
        )
    )
    return registry
