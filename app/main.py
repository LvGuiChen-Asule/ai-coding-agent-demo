"""FastAPI 入口：把 Agent 工作流暴露为 REST API，并托管 Web UI。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent_core import AgentWorkflow, create_provider
from agent_core.config import settings
from agent_core.tools import build_registry


class RunRequest(BaseModel):
    """工作流运行请求。"""

    requirement: str
    stack: Optional[str] = None  # springboot | python | node
    provider: Optional[str] = None  # mock | openai | qwen
    workspace: Optional[str] = None
    demo_bug: bool = False
    max_fix_iterations: Optional[int] = None


WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"

app = FastAPI(
    title="AI Coding Agent Demo API",
    description="基于 Agent Workflow 的智能代码开发助手 Demo",
    version="0.1.0",
)


@app.get("/")
def index() -> FileResponse:
    """Web UI。"""
    return FileResponse(WEBUI_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "provider": settings.llm_provider}


@app.get("/api/tools")
def list_tools() -> dict:
    """列出 Tool Calling 系统中已注册的工具。"""
    registry = build_registry(Path(settings.workspace_root))
    return {"tools": registry.list_tools()}


@app.post("/api/workflow/run")
def run_workflow(req: RunRequest) -> dict:
    """执行一次完整 Agent 工作流（创建或修改项目）。"""
    workflow = AgentWorkflow(
        provider=create_provider(req.provider),
        workspace=req.workspace or settings.workspace_root,
        max_fix_iterations=req.max_fix_iterations,
        demo_bug=req.demo_bug,
    )
    result = workflow.run(req.requirement, stack=req.stack)
    return result.to_dict()

