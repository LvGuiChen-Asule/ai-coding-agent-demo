"""端到端工作流测试（MockProvider 离线模式）。"""

import json
import tempfile
import unittest
from pathlib import Path

from agent_core import AgentWorkflow


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_springboot_login_module(self):
        wf = AgentWorkflow(workspace=self.root / "sb")
        result = wf.run("帮我创建一个SpringBoot用户登录模块")
        self.assertTrue(result.generated_files)
        self.assertTrue(result.test_report.ok)
        self.assertIsNotNone(result.review_report)
        self.assertTrue((self.root / "sb" / "pom.xml").exists())
        self.assertTrue((self.root / "sb" / "CODE_REVIEW_REPORT.md").exists())
        self.assertTrue((self.root / "sb" / "workflow_result.json").exists())

    def test_review_finds_issues(self):
        wf = AgentWorkflow(workspace=self.root / "sb2")
        result = wf.run("帮我创建一个SpringBoot用户登录模块")
        severities = {i.severity for i in result.review_report.issues}
        self.assertIn("critical", severities)  # Mapper XML ${} 注入
        self.assertIn("high", severities)  # 硬编码口令 / 查询逻辑

    def test_python_stack_runs_real_tests(self):
        wf = AgentWorkflow(workspace=self.root / "py")
        result = wf.run("创建一个Python FastAPI用户接口", stack="python")
        self.assertTrue(result.test_report.ok)
        self.assertIn("自动化测试运行", [c["name"] for c in result.test_report.checks])

    def test_modify_adds_captcha(self):
        root = self.root / "mod"
        wf1 = AgentWorkflow(workspace=root)
        wf1.run("帮我创建一个SpringBoot用户登录模块")

        wf2 = AgentWorkflow(workspace=root)
        result = wf2.run("修改登录逻辑，增加验证码校验")
        service = (root / "src/main/java/com/example/userlogin/service/impl/UserServiceImpl.java")
        self.assertTrue(service.exists())
        content = service.read_text(encoding="utf-8")
        self.assertIn("getCaptcha", content)

    def test_demo_bug_triggers_fix_loop(self):
        wf = AgentWorkflow(workspace=self.root / "bug", demo_bug=True)
        result = wf.run("创建一个Python FastAPI用户接口", stack="python")
        self.assertTrue(result.test_report.ok)
        self.assertGreaterEqual(result.fix_iterations, 1)


if __name__ == "__main__":
    unittest.main()
