"""Test Agent：自动运行测试并做静态验证，输出结构化测试报告。"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from .tools import ToolRegistry
from .types import TestReport


class TestAgent:
    """自动测试与错误分析 Agent。"""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def run(self, workspace: Path, stack: str, requirement: str = "") -> TestReport:
        checks: list[dict] = []
        errors: list[str] = []

        if stack == "springboot":
            checks = self._static_check_java(workspace)
        elif stack == "python":
            checks = self._static_check_python(workspace)
        elif stack == "node":
            checks = self._static_check_node(workspace)
        else:
            checks = [{"name": "结构校验", "ok": True, "detail": "跳过"}]

        for check in checks:
            if not check["ok"]:
                errors.append(f"{check['name']}: {check['detail']}")

        # 真实测试运行器（若可用）
        runner_output = ""
        runner_ok = True
        runner_note = ""
        has_real_runner = False
        if stack == "springboot" and (shutil.which("mvn") or (workspace / "mvnw").exists()):
            has_real_runner = True
            result = self.registry.call("TestRunner", {"cwd": "."})
            runner_ok, runner_output = result.ok, result.output
        elif stack == "python":
            result = self.registry.call("TestRunner", {"cwd": "."})
            if result.ok or "未检测到" not in (result.error or ""):
                has_real_runner = True
                runner_ok, runner_output = result.ok, result.output
        elif stack == "node" and shutil.which("npm"):
            result = self.registry.call("TestRunner", {"cwd": "."})
            has_real_runner = True
            runner_ok, runner_output = result.ok, result.output

        if has_real_runner:
            checks.append(
                {"name": "自动化测试运行", "ok": runner_ok, "detail": runner_output[:800]}
            )
            if not runner_ok:
                errors.append(f"自动化测试失败: {runner_output[:500]}")
        elif stack == "springboot":
            runner_note = "未检测到 Maven，执行静态结构校验代替；安装 Maven 后可用 `mvn test` 运行真实测试。"
            checks.append({"name": "测试环境", "ok": True, "detail": runner_note})

        summary_lines = [
            f"共 {len(checks)} 项检查，{sum(1 for c in checks if c['ok'])} 项通过。"
        ]
        if runner_note:
            summary_lines.append(runner_note)
        return TestReport(
            ok=not errors,
            command="auto-detect",
            summary="；".join(summary_lines),
            output=runner_output,
            checks=checks,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # 静态结构校验

    def _static_check_java(self, workspace: Path) -> list[dict]:
        checks: list[dict] = []
        java_files = [p for p in workspace.rglob("*.java")]
        xml_files = [p for p in workspace.rglob("*.xml")]
        sql_files = list(workspace.rglob("*.sql"))

        required = [
            "pom.xml",
            "src/main/resources/application.yml",
            "src/main/resources/schema.sql",
        ]
        required_classes = [
            "entity/User.java",
            "mapper/UserMapper.java",
            "service/UserService.java",
            "controller/UserController.java",
        ]
        missing = [f for f in required if not (workspace / f).exists()]
        missing += [
            f for f in required_classes
            if not list(workspace.rglob(f.split("/")[-1]))
        ]
        checks.append(
            {
                "name": "关键文件完整性",
                "ok": not missing,
                "detail": "缺失: " + ", ".join(missing) if missing
                else f"{len(required) + len(required_classes)} 个关键文件齐全",
            }
        )

        # XML 合法性
        xml_ok = True
        xml_detail = []
        for xml_path in xml_files:
            try:
                ET.parse(xml_path)
            except ET.ParseError as exc:
                xml_ok = False
                xml_detail.append(f"{xml_path.name}: {exc}")
        checks.append(
            {
                "name": "XML 格式校验",
                "ok": xml_ok,
                "detail": "；".join(xml_detail) or f"{len(xml_files)} 个 XML 均合法",
            }
        )

        # Java 括号配平
        unbalanced = []
        for path in java_files:
            content = path.read_text(encoding="utf-8", errors="replace")
            if content.count("{") != content.count("}"):
                unbalanced.append(path.name)
        checks.append(
            {
                "name": "Java 括号配平",
                "ok": not unbalanced,
                "detail": "异常: " + ", ".join(unbalanced) if unbalanced
                else f"{len(java_files)} 个 Java 文件括号配平",
            }
        )

        # SQL 结构
        sql_ok = True
        sql_detail = "未找到 schema.sql"
        if sql_files:
            sql = sql_files[0].read_text(encoding="utf-8", errors="replace")
            sql_ok = "CREATE TABLE" in sql.upper() and "sys_user" in sql
            sql_detail = "包含 CREATE TABLE 与 sys_user 表" if sql_ok else "缺少建表语句或 sys_user 表"
        checks.append({"name": "SQL 结构校验", "ok": sql_ok, "detail": sql_detail})

        # 依赖引用完整性
        ref_ok = True
        ref_detail = []
        all_content = "\n".join(
            p.read_text(encoding="utf-8", errors="replace") for p in java_files
        )
        for ref in ("UserService", "UserMapper", "UserController"):
            if ref not in all_content:
                ref_ok = False
                ref_detail.append(f"缺少对 {ref} 的引用")
        checks.append(
            {
                "name": "类依赖引用完整性",
                "ok": ref_ok,
                "detail": "；".join(ref_detail) or "Controller/Service/Mapper 引用链完整",
            }
        )
        return checks

    def _static_check_python(self, workspace: Path) -> list[dict]:
        checks: list[dict] = []
        py_files = [p for p in workspace.rglob("*.py")]
        missing = [
            f for f in ("user_service.py", "test_user_service.py", "main.py")
            if not list(workspace.rglob(f))
        ]
        checks.append(
            {
                "name": "关键文件完整性",
                "ok": not missing,
                "detail": "缺失: " + ", ".join(missing) if missing
                else f"{len(py_files)} 个 Python 文件齐全",
            }
        )
        syntax_errors = []
        for path in py_files:
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except SyntaxError as exc:
                syntax_errors.append(f"{path.name}:{exc.lineno} {exc.msg}")
        checks.append(
            {
                "name": "Python 语法编译",
                "ok": not syntax_errors,
                "detail": "；".join(syntax_errors) or f"{len(py_files)} 个 Python 文件编译通过",
            }
        )
        return checks

    def _static_check_node(self, workspace: Path) -> list[dict]:
        checks: list[dict] = []
        js_files = [p for p in workspace.rglob("*.js")]
        pkg = workspace / "package.json"
        pkg_ok = pkg.exists() and '"test"' in pkg.read_text(encoding="utf-8")
        checks.append(
            {
                "name": "package.json 与 test 脚本",
                "ok": pkg_ok,
                "detail": "存在 test 脚本" if pkg_ok else "缺少 package.json 或 test 脚本",
            }
        )
        checks.append(
            {
                "name": "Node 源文件完整性",
                "ok": len(js_files) >= 3,
                "detail": f"{len(js_files)} 个 JS 文件",
            }
        )
        return checks

