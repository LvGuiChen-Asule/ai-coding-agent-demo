"""项目上下文分析：扫描目录结构、读取文件、定位目标代码。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class ProjectContext:
    """一次工作流运行期间的项目快照。"""

    def __init__(self, root: Path) -> None:
        self.root = root

    def tree(self, max_depth: int = 4) -> list[dict]:
        """返回目录树（相对路径 + 文件大小）。"""
        entries: list[dict] = []

        def walk(dirpath: Path, depth: int) -> None:
            if depth > max_depth:
                return
            for child in sorted(dirpath.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if child.name.startswith(".") or child.name in ("__pycache__", "node_modules"):
                    continue
                rel = str(child.relative_to(self.root)).replace("\\", "/")
                if child.is_dir():
                    entries.append({"path": rel, "type": "dir"})
                    walk(child, depth + 1)
                else:
                    entries.append(
                        {"path": rel, "type": "file", "size": child.stat().st_size}
                    )

        if self.root.exists():
            walk(self.root, 0)
        return entries

    def files(self, suffixes: Optional[list[str]] = None) -> list[Path]:
        """列出项目文件，可按扩展名过滤。"""
        if not self.root.exists():
            return []
        files = [p for p in self.root.rglob("*") if p.is_file()]
        if suffixes:
            files = [p for p in files if p.suffix.lower() in suffixes]
        return sorted(files)

    def read(self, rel_path: str, with_lines: bool = False) -> str:
        """读取文件内容；with_lines=True 时每行加行号前缀。"""
        path = self._resolve(rel_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {rel_path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        if not with_lines:
            return content
        lines = content.splitlines()
        width = len(str(len(lines)))
        return "\n".join(f"{i + 1:>{width}} | {line}" for i, line in enumerate(lines))

    def find_files_by_keyword(self, keyword: str, suffixes: Optional[list[str]] = None) -> list[str]:
        """按文件名关键词定位文件（如 Controller / Service / Mapper）。"""
        hits = []
        for path in self.files(suffixes):
            if keyword.lower() in path.name.lower():
                hits.append(str(path.relative_to(self.root)).replace("\\", "/"))
        return hits

    def find_in_content(self, pattern: str, suffixes: Optional[list[str]] = None) -> list[dict]:
        """在文件内容中搜索关键词，返回 {path, line, text}。"""
        hits: list[dict] = []
        for path in self.files(suffixes):
            try:
                for lineno, line in enumerate(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(),
                    start=1,
                ):
                    if pattern in line:
                        hits.append(
                            {
                                "path": str(path.relative_to(self.root)).replace("\\", "/"),
                                "line": lineno,
                                "text": line.strip(),
                            }
                        )
            except OSError:
                continue
        return hits

    def _resolve(self, rel_path: str) -> Path:
        """解析相对路径并防止目录穿越。"""
        path = (self.root / rel_path).resolve()
        root = self.root.resolve()
        if not str(path).startswith(str(root)):
            raise PermissionError(f"路径超出工作区，已拒绝: {rel_path}")
        return path


def scan_project(root: Path) -> dict:
    """便捷函数：返回项目扫描摘要。"""
    ctx = ProjectContext(root)
    return {
        "root": str(root),
        "exists": root.exists(),
        "files": len(ctx.files()),
        "tree": ctx.tree(),
    }
