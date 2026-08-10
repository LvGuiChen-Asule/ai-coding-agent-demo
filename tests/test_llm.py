"""LLM Provider 层测试。"""

import unittest

from agent_core.llm import MockProvider, extract_json
from agent_core.prompts import (
    CODER_SYSTEM,
    PLANNER_SYSTEM,
    REVIEWER_SYSTEM,
)


class ExtractJsonTest(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})

    def test_fenced_json(self):
        text = "思考过程...\n```json\n{\"steps\": [1, 2]}\n```\n结束"
        self.assertEqual(extract_json(text), {"steps": [1, 2]})

    def test_nested_json_with_braces(self):
        text = '{"detail": {"files": ["a.java"]}}'
        self.assertEqual(extract_json(text), {"detail": {"files": ["a.java"]}})

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            extract_json("没有任何 JSON")


class MockProviderTest(unittest.TestCase):
    def setUp(self):
        self.provider = MockProvider()

    def test_plan_routing(self):
        raw = self.provider.complete_json(
            PLANNER_SYSTEM,
            '{"requirement": "帮我创建一个SpringBoot用户登录模块", "stack": "springboot", "project": {}}',
        )
        self.assertIn("task", raw)
        self.assertGreaterEqual(len(raw["steps"]), 5)

    def test_coder_routing(self):
        raw = self.provider.complete_json(
            CODER_SYSTEM,
            '{"requirement": "x", "step": {"detail": {"files": ["a.py"]}}, "project": {"stack": "python"}}',
        )
        self.assertIn("files", raw)

    def test_review_routing_not_confused_by_suggestion_keyword(self):
        """审查提示词里的「修改建议」不应把请求路由到修改分支。"""
        raw = self.provider.complete_json(
            REVIEWER_SYSTEM,
            '{"files": {"a.java": "public class A { int x; }"}}',
        )
        self.assertIn("score", raw)
        self.assertIn("issues", raw)


if __name__ == "__main__":
    unittest.main()

