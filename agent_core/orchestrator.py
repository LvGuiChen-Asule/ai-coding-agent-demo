"""AgentWorkflow 编排器。

将 Planner -> CodeGen -> FileOp -> Test -> FixLoop -> Reflection 串成
一条完整流水线，模拟真实 AI 软件工程师的开发闭环。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .coder import CodeGenAgent
from .config import settings
from .context import ProjectContext
from .fileops import FileOpAgent
from .llm import BaseLLMProvider, create_provider
from .planner import PlannerAgent
from .reflector import ReflectionAgent
from .tester import TestAgent
from .tools import build_registry
from .types import Event, GeneratedFile, TaskPlan, TestReport, WorkflowResult


class AgentWorkflow:
    """AI Coding Agent 工作流。"""

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        workspace: Optional[Path | str] = None,
        max_fix_iterations: Optional[int] = None,
        demo_bug: bool = False,
    ) -> None:
        self.provider = provider or create_provider()
        self.workspace = Path(workspace or settings.workspace_root).resolve()
        self.max_fix_iterations = (
            max_fix_iterations if max_fix_iterations is not None else settings.max_fix_iterations
        )
        self.registry = build_registry(self.workspace)
        self.planner = PlannerAgent(self.provider)
        self.coder = CodeGenAgent(self.provider)
        self.fileops = FileOpAgent(self.registry)
        self.tester = TestAgent(self.registry)
        self.reflector = ReflectionAgent(self.provider)
        self.events: list[Event] = []
        self.demo_bug = demo_bug

    # ------------------------------------------------------------------

    def log(self, stage: str, agent: str, message: str, detail: Optional[dict] = None) -> None:
        self.events.append(Event(stage=stage, agent=agent, message=message, detail=detail or {}))

    def run(self, requirement: str, stack: Optional[str] = None) -> WorkflowResult:
        """执行一次完整工作流（创建或修改项目）。"""
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.log("start", "Orchestrator", f"收到需求：{requirement}", {"requirement": requirement})

        plan = self.planner.plan(requirement, stack)
        stack = str(plan.meta.get("stack", stack or "springboot"))
        project = dict(plan.meta.get("project", {}))
        project["stack"] = stack
        result = WorkflowResult(
            requirement=requirement,
            provider=self.provider.name,
            plan=plan,
            workspace=str(self.workspace),
        )
        self.log(
            "plan",
            "PlannerAgent",
            f"任务规划完成：{len(plan.steps)} 个步骤",
            {"task": plan.task, "stack": stack, "steps": [s.title for s in plan.steps]},
        )

        generated: list[GeneratedFile] = []
        test_report: Optional[TestReport] = None
        ran_test = False

        for step in plan.steps:
            self.log("plan", "PlannerAgent", f"开始步骤 {step.id}：{step.title}", step.to_dict())
            if step.step_type == "codegen":
                generated += self._do_codegen(requirement, step, project)
            elif step.step_type == "modify":
                generated += self._do_modify(requirement, step, project)
            elif step.step_type == "test":
                test_report = self._do_test(requirement, stack)
                ran_test = True
                test_report = self._fix_loop(requirement, stack, test_report, step, project, generated)
                result.fix_iterations = self._last_fix_iterations

        # 没有测试步骤时（如纯修改流程），结束后自动补一轮验证
        if not ran_test:
            test_report = self._do_test(requirement, stack)
            result.fix_iterations = 0

        result.generated_files = self._dedupe_files(generated)
        result.test_report = test_report

        # Reflection：自我检查与优化
        self.log("reflect", "ReflectionAgent", "开始代码审查与自我优化")
        all_files = self.fileops.read_all_project_files()
        review = self.reflector.review(all_files, self.workspace)
        result.review_report = review
        self.log(
            "reflect",
            "ReflectionAgent",
            f"审查完成：评分 {review.score}/100，发现 {len(review.issues)} 个问题",
            {"score": review.score, "issues": len(review.issues), "report": "CODE_REVIEW_REPORT.md"},
        )

        result.events = self.events
        self.log("done", "Orchestrator", "工作流执行完毕", {"workspace": str(self.workspace)})
        self._save_result(result)
        return result

    # ------------------------------------------------------------------

    def _do_codegen(self, requirement: str, step, project: dict) -> list[GeneratedFile]:
        files = self.coder.generate(requirement, step, project)
        if self.demo_bug and project.get("stack") == "python":
            files = self._inject_demo_bug(files)
        if not files:
            self.log("codegen", "CodeGenAgent", f"步骤 {step.id} 未生成文件，跳过", {"step": step.title})
            return []
        writes = self.fileops.write_files(files, reason=step.title)
        self.log(
            "codegen",
            "CodeGenAgent",
            f"生成并写入 {len(files)} 个文件",
            {"files": [f.path for f in files]},
        )
        self.log("fileop", "FileOpAgent", "文件落盘完成（已记录 diff）", {"written": [w["path"] for w in writes]})
        return files

    @staticmethod
    def _inject_demo_bug(files: list[GeneratedFile]) -> list[GeneratedFile]:
        """Demo 专用：向 user_service.py 注入一个确定性 Bug，触发测试失败。"""
        poisoned = []
        for file in files:
            if file.path.endswith("user_service.py"):
                content = file.content.replace(
                    "    token = secrets.token_hex(16)",
                    "    token = secrets.token_hex(16)\n"
                    "    # [demo-bug] 模拟生成的代码缺陷：登录永远抛异常\n"
                    "    raise RuntimeError(\"demo bug: login always fails\")",
                )
                poisoned.append(GeneratedFile(path=file.path, content=content, reason=file.reason))
            else:
                poisoned.append(file)
        return poisoned

    def _do_modify(self, requirement: str, step, project: dict) -> list[GeneratedFile]:
        existing = self.fileops.read_all_project_files()
        files = self.coder.generate(requirement, step, project, existing_files=existing)
        if not files:
            self.log(
                "modify",
                "FileOpAgent",
                "未识别到可自动化修改点，跳过修改",
                {"intent": step.detail.get("note", "")},
            )
            return []
        writes = self.fileops.write_files(files, reason=step.title)
        self.log(
            "modify",
            "FileOpAgent",
            f"修改完成：{len(files)} 个文件已更新（含 diff 记录）",
            {"files": [w["path"] for w in writes], "diff": [w["diff"] for w in writes]},
        )
        return files

    def _do_test(self, requirement: str, stack: str) -> TestReport:
        report = self.tester.run(self.workspace, stack, requirement)
        status = "通过" if report.ok else "失败"
        self.log(
            "test",
            "TestAgent",
            f"测试{status}：{report.summary}",
            {"ok": report.ok, "checks": report.checks, "errors": report.errors},
        )
        return report

    def _fix_loop(
        self,
        requirement: str,
        stack: str,
        report: TestReport,
        step,
        project: dict,
        generated: list[GeneratedFile],
    ) -> TestReport:
        """测试失败时自动分析并修复（最多 max_fix_iterations 轮）。"""
        iteration = 0
        current = report
        while not current.ok and iteration < self.max_fix_iterations:
            iteration += 1
            self._last_fix_iterations = iteration
            self.log(
                "fix",
                "FixerAgent",
                f"测试未通过，进入自动修复第 {iteration} 轮",
                {"errors": current.errors[:3]},
            )
            target_files = self._files_from_errors(current.errors)
            existing = self.fileops.read_all_project_files()
            fix_errors = current.errors[:5]
            if not target_files:
                self.log(
                    "fix",
                    "FixerAgent",
                    "测试报告未定位到具体失败文件，跳过本轮重写",
                    {"errors": current.errors[:3]},
                )
                break
            files = self.coder.generate(
                requirement, step, project, existing_files=existing, fix_errors=fix_errors
            )
            if files:
                writes = self.fileops.write_files(files, reason=f"自动修复第 {iteration} 轮")
                generated.extend(files)
                self.log(
                    "fix",
                    "FixerAgent",
                    f"已重写 {len(files)} 个文件",
                    {"files": [w["path"] for w in writes]},
                )
            current = self.tester.run(self.workspace, stack, requirement)
            status = "通过" if current.ok else "仍失败"
            self.log(
                "test",
                "TestAgent",
                f"第 {iteration} 轮修复后测试{status}：{current.summary}",
                {"ok": current.ok, "errors": current.errors},
            )
            if current.ok:
                break
        self._last_fix_iterations = iteration
        return current

    @staticmethod
    def _files_from_errors(errors: list[str]) -> list[str]:
        files = set()
        pattern = re.compile(r"[\w./-]+\.(?:java|py|js)")
        for err in errors:
            for match in pattern.findall(err):
                if not match.startswith((".", "/")):
                    files.add(match)
        return sorted(files)[:10]

    @staticmethod
    def _dedupe_files(files: list[GeneratedFile]) -> list[GeneratedFile]:
        by_path: dict[str, GeneratedFile] = {}
        for f in files:
            by_path[f.path] = f
        return list(by_path.values())

    def _save_result(self, result: WorkflowResult) -> None:
        path = self.workspace / "workflow_result.json"
        path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def project_tree(self) -> list[dict]:
        return ProjectContext(self.workspace).tree()
