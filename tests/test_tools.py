"""Tool Calling 工具系统测试。"""

import tempfile
import unittest
from pathlib import Path

from agent_core.tools import build_registry


class ToolRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = build_registry(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_tools(self):
        names = {t["name"] for t in self.registry.list_tools()}
        self.assertEqual(
            names, {"FileReader", "FileWriter", "Terminal", "Git", "TestRunner"}
        )

    def test_file_writer_creates_and_backs_up(self):
        r1 = self.registry.call("FileWriter", {"path": "a.py", "content": "print(1)\n"})
        self.assertTrue(r1.ok)
        self.assertTrue((self.root / "a.py").exists())

        r2 = self.registry.call("FileWriter", {"path": "a.py", "content": "print(2)\n"})
        self.assertTrue(r2.ok)
        self.assertIn("diff", r2.data)
        backups = list((self.root / ".agent_backups").iterdir())
        self.assertEqual(len(backups), 1)

    def test_path_traversal_denied(self):
        result = self.registry.call("FileWriter", {"path": "../evil.txt", "content": "x"})
        self.assertFalse(result.ok)

    def test_unknown_tool(self):
        result = self.registry.call("NotExist", {})
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()

