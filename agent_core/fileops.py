"""File Operation Agent：通过工具调用落盘 / 读取文件，记录 diff。"""

from __future__ import annotations

from typing import Optional

from .tools import ToolRegistry
from .types import GeneratedFile


class FileOpAgent:
    """文件操作 Agent：依赖 Tool Calling 系统中的 FileReader / FileWriter。"""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def write_files(self, files: list[GeneratedFile], reason: str = "") -> list[dict]:
        """写入一批生成文件，返回每个文件的写盘结果（含 diff）。"""
        results: list[dict] = []
        for file in files:
            result = self.registry.call(
                "FileWriter",
                {"path": file.path, "content": file.content, "reason": reason or file.reason},
            )
            results.append(
                {
                    "path": file.path,
                    "ok": result.ok,
                    "diff": result.data.get("diff", ""),
                    "error": result.error,
                }
            )
            if not result.ok:
                raise RuntimeError(f"写入失败 {file.path}: {result.error}")
        return results

    def read_files(self, paths: list[str]) -> dict[str, str]:
        """读取工作区内一批文件的内容（供修改流程使用）。"""
        contents: dict[str, str] = {}
        for path in paths:
            result = self.registry.call("FileReader", {"path": path})
            if result.ok:
                contents[path] = result.output
        return contents

    def read_all_project_files(self, suffixes: Optional[list[str]] = None) -> dict[str, str]:
        """读取整个项目（工作区）中所有文本文件。"""
        workspace = self.registry.workspace
        if not workspace.exists():
            return {}
        contents: dict[str, str] = {}
        skip_names = {".git", ".agent_backups", "__pycache__", ".pytest_cache", "node_modules"}
        skip_rel = {"workflow_result.json", "CODE_REVIEW_REPORT.md"}
        for path in workspace.rglob("*"):
            if any(part in skip_names for part in path.relative_to(workspace).parts):
                continue
            if not path.is_file():
                continue
            if suffixes and path.suffix.lower() not in suffixes:
                continue
            rel = str(path.relative_to(workspace)).replace("\\", "/")
            if rel in skip_rel:
                continue
            try:
                contents[rel] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        return contents
