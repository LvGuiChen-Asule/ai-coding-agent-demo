"""Code Generation Agent：根据任务步骤生成 / 修改代码。"""

from __future__ import annotations

import json
from typing import Any, Optional

from .llm import BaseLLMProvider
from .prompts import CODER_SYSTEM, PATCHER_SYSTEM
from .types import GeneratedFile, TaskStep
from templates import (
    apply_captcha_to_springboot,
    apply_token_to_springboot,
    render_nodejs,
    render_python_fastapi,
    render_springboot,
)

_ALLOWED_SUFFIXES = {
    ".java", ".py", ".js", ".ts", ".xml", ".yml", ".yaml", ".sql",
    ".json", ".md", ".txt", ".properties", ".html", ".css", ".env.example",
}


def _render_all(stack: str, project: dict[str, Any]) -> dict[str, str]:
    if stack == "springboot":
        return render_springboot(project)
    if stack == "python":
        return render_python_fastapi(project)
    if stack == "node":
        return render_nodejs(project)
    return render_springboot(project)


def mock_generate(requirement: str, step: dict[str, Any], project: dict[str, Any]) -> dict[str, str]:
    """离线代码生成：渲染模板并按步骤的目标文件过滤。"""
    stack = project.get("stack", detect_stack_from_project(project))
    all_files = _render_all(stack, project)
    wanted = [f for f in step.get("detail", {}).get("files", [])]
    if not wanted:
        return all_files
    return {k: v for k, v in all_files.items() if k in wanted}


def detect_stack_from_project(project: dict[str, Any]) -> str:
    if "package" in project or "artifact" in project:
        return "springboot"
    if "pkg" in project:
        return "python"
    return "node"


def mock_modify(
    requirement: str,
    project: dict[str, Any],
    existing_files: dict[str, str],
) -> dict[str, str]:
    """离线修改：识别修改意图并打补丁。"""
    intent = "add_captcha" if any(k in requirement for k in ("验证码", "captcha")) else (
        "add_token" if any(k in requirement for k in ("token", "jwt", "登录态")) else "generic"
    )
    if intent == "add_captcha":
        patched = apply_captcha_to_springboot(existing_files)
    elif intent == "add_token":
        patched = apply_token_to_springboot(existing_files)
    else:
        patched = {}
    # generic：仅返回原文件，工作流记录「未识别到可自动化修改点」
    return {k: v for k, v in patched.items() if existing_files.get(k) != v}


class CodeGenAgent:
    """代码生成 Agent：LLM 生成，失败时回退离线模板。"""

    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    def generate(
        self,
        requirement: str,
        step: TaskStep,
        project: dict[str, Any],
        existing_files: Optional[dict[str, str]] = None,
        fix_errors: Optional[list[str]] = None,
    ) -> list[GeneratedFile]:
        stack = project.get("stack", "")
        user = json.dumps(
            {
                "requirement": requirement,
                "step": step.to_dict(),
                "project": project,
                "existing_files": existing_files or {},
                "fix_errors": fix_errors or [],
            },
            ensure_ascii=False,
        )
        system = PATCHER_SYSTEM if step.step_type == "modify" else CODER_SYSTEM
        try:
            raw = self.provider.complete_json(system, user, temperature=0.4, max_tokens=4096)
            files = [
                GeneratedFile(
                    path=str(f["path"]),
                    content=str(f["content"]),
                    reason=step.title,
                )
                for f in raw.get("files", [])
                if self._valid_path(f.get("path", ""))
            ]
            if fix_errors:
                files = [f for f in files if self._matches_errors(f.path, fix_errors)] or files
            if files:
                return files
        except Exception:
            pass
        return self._fallback(requirement, step, project, existing_files)

    def _fallback(
        self,
        requirement: str,
        step: TaskStep,
        project: dict[str, Any],
        existing_files: Optional[dict[str, str]] = None,
    ) -> list[GeneratedFile]:
        if step.step_type == "modify":
            changed = mock_modify(requirement, project, existing_files or {})
            return [
                GeneratedFile(path=path, content=content, reason=step.title)
                for path, content in changed.items()
            ]
        files = mock_generate(requirement, step.to_dict(), project)
        return [
            GeneratedFile(path=path, content=content, reason=step.title)
            for path, content in files.items()
        ]

    @staticmethod
    def _matches_errors(path: str, fix_errors: list[str]) -> bool:
        basename = path.split("/")[-1]
        return any(basename in err or path in err for err in fix_errors)

    @staticmethod
    def _valid_path(path: str) -> bool:
        if not path or path.startswith("/") or ".." in path.split("/"):
            return False
        return any(path.lower().endswith(sfx) for sfx in _ALLOWED_SUFFIXES)
