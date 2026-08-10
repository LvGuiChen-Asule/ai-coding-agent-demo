"""Reflection Agent：代码审查与自我优化。"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .llm import BaseLLMProvider
from .prompts import REVIEWER_SYSTEM
from .types import ReviewIssue, ReviewReport


def mock_review(files: dict[str, str]) -> dict:
    """离线审查：基于启发式规则发现质量问题与安全隐患。"""
    issues: list[ReviewIssue] = []
    strengths: list[str] = []

    def add(severity: str, path: str, title: str, detail: str, suggestion: str, line: int | None = None) -> None:
        issues.append(
            ReviewIssue(
                severity=severity,
                file=path,
                title=title,
                detail=detail,
                suggestion=suggestion,
                line=line,
            )
        )

    for path, content in files.items():
        # SQL 注入风险（仅检查 Mapper XML；pom.xml 中的 ${} 是 Maven 属性语法）
        if "${" in content and path.endswith(".xml") and "mapper" in path.lower():
            add(
                "critical",
                path,
                "SQL 注入风险",
                "XML 映射中使用了 ${} 直接拼接参数，存在 SQL 注入风险。",
                "改为 #{keyword} 参数化查询，或对关键字做白名单 / 转义处理。",
            )
        # 弱密码哈希
        if "MessageDigest" in content and "SHA-256" in content and "salt" not in content.lower():
            add(
                "medium",
                path,
                "密码哈希强度不足",
                "使用无盐 SHA-256 存储密码，易被彩虹表破解。",
                "改用 BCrypt / Argon2 加盐哈希（如 spring-security-crypto 的 BCryptPasswordEncoder）。",
            )
        # 硬编码口令
        if re.search(r"password\s*[:=]\s*[\"']", content) and path.endswith(
            (".yml", ".yaml", ".properties", ".env.example")
        ):
            add(
                "high",
                path,
                "硬编码数据库口令",
                "配置文件中出现明文密码，存在泄露风险。",
                "改用环境变量注入，并将 .env 加入 .gitignore。",
            )
        # 逻辑错误：getById 使用用户名查询
        if 'findByUsername("id:"' in content:
            add(
                "high",
                path,
                "查询逻辑错误",
                "getById 通过 findByUsername 拼接字符串查询，无法按主键正确查询。",
                "新增 findById 方法并使用 #{id} 参数化查询。",
            )
        # SELECT *
        if "SELECT *" in content.upper() and path.endswith(".xml"):
            add(
                "low",
                path,
                "避免 SELECT *",
                "全字段查询会带来不必要的 IO 与耦合。",
                "显式列出所需字段。",
            )
        # TODO / FIXME
        for match in re.finditer(r"(TODO|FIXME)[^\n]*", content):
            add(
                "low",
                path,
                "遗留 TODO 标记",
                f"代码中遗留待办标记：{match.group(0).strip()}",
                "按标记内容完善实现后移除。",
            )

    # 重复代码检测（按行指纹）
    fingerprints: Counter = Counter()
    for content in files.values():
        for line in content.splitlines():
            stripped = line.strip()
            if 8 <= len(stripped) <= 80 and not stripped.startswith(("#", "//", "/*", "*")):
                fingerprints[stripped] += 1
    dupes = [fp for fp, count in fingerprints.items() if count >= 3]
    if dupes:
        add(
            "medium",
            "(全局)",
            "存在重复代码",
            f"检测到 {len(dupes)} 处重复行模式，维护成本高。",
            "提取公共方法 / 基类 / 工具类消除重复。",
        )

    # Controller 复杂度
    for path, content in files.items():
        if path.endswith("Controller.java") and len(content.splitlines()) > 150:
            add(
                "low",
                path,
                "Controller 过于复杂",
                "Controller 行数较多，可能承担了过多职责。",
                "将校验与业务逻辑下沉到 Service 层，保持 Controller 薄。",
            )

    all_text = "\n".join(files.values())
    if "mybatis" in all_text.lower():
        strengths.append("分层清晰：Controller / Service / Mapper 职责分离")
    if "jakarta.validation" in all_text or "@NotBlank" in all_text:
        strengths.append("接口层使用了 Bean Validation 参数校验")
    if "MockMvc" in all_text:
        strengths.append("包含 MockMvc 接口测试，覆盖注册与登录主流程")
    if "userMapper.insert" in all_text:
        strengths.append("数据写入使用参数化 SQL，整体上避免了拼接注入")
    if not strengths:
        strengths.append("代码结构完整，包含实体 / 服务 / 接口 / 测试")

    weights = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 1}
    score = max(0, 100 - sum(weights.get(i.severity, 1) for i in issues))
    severity_count = Counter(i.severity for i in issues)
    if issues:
        summary = (
            f"共发现 {len(issues)} 个问题"
            f"（critical {severity_count['critical']} / high {severity_count['high']} / "
            f"medium {severity_count['medium']} / low {severity_count['low']}），综合评分 {score}/100。"
        )
    else:
        summary = f"未发现问题，代码质量良好，综合评分 {score}/100。"
    suggestions = [
        "优先修复 critical / high 级别问题（SQL 注入、明文口令、查询逻辑）。",
        "密码存储升级为 BCrypt，并移除硬编码配置。",
        "补充更多边界用例（重复注册、空参数、非法字符）。",
    ]
    return {
        "score": score,
        "summary": summary,
        "issues": [i.to_dict() for i in issues],
        "strengths": strengths,
        "suggestions": suggestions,
    }


class ReflectionAgent:
    """Reflection Agent：LLM 审查 + 离线规则回退，并产出 Markdown 报告。"""

    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    def review(self, files: dict[str, str], workspace: Path) -> ReviewReport:
        # 内容裁剪，防止超长
        trimmed = {}
        for path, content in list(files.items())[:20]:
            trimmed[path] = content[:6000]

        user = json.dumps({"files": trimmed}, ensure_ascii=False)
        try:
            raw = self.provider.complete_json(REVIEWER_SYSTEM, user, temperature=0.2, max_tokens=3000)
            report = ReviewReport(
                score=int(raw.get("score", 80)),
                summary=str(raw.get("summary", "")),
                issues=[
                    ReviewIssue(
                        severity=str(i.get("severity", "info")),
                        file=str(i.get("file", "")),
                        title=str(i.get("title", "")),
                        detail=str(i.get("detail", "")),
                        suggestion=str(i.get("suggestion", "")),
                        line=i.get("line"),
                    )
                    for i in raw.get("issues", [])
                ],
                strengths=[str(s) for s in raw.get("strengths", [])],
                suggestions=[str(s) for s in raw.get("suggestions", [])],
            )
        except Exception:
            raw = mock_review(files)
            report = ReviewReport(
                score=int(raw["score"]),
                summary=str(raw["summary"]),
                issues=[ReviewIssue(**i) for i in raw["issues"]],
                strengths=list(raw["strengths"]),
                suggestions=list(raw["suggestions"]),
            )

        self._write_report(report, workspace)
        return report

    @staticmethod
    def _write_report(report: ReviewReport, workspace: Path) -> None:
        lines = [
            "# Code Review Report",
            "",
            f"**综合评分：{report.score}/100**",
            "",
            report.summary,
            "",
            "## 问题清单",
            "",
            "| 严重级别 | 文件 | 问题 | 建议 |",
            "| --- | --- | --- | --- |",
        ]
        for issue in report.issues:
            lines.append(
                f"| {issue.severity} | `{issue.file}` | {issue.title} | {issue.suggestion} |"
            )
        if not report.issues:
            lines.append("| - | - | 未发现问题 | - |")
        lines += ["", "## 亮点", ""]
        lines += [f"- {s}" for s in report.strengths] or ["- 无"]
        lines += ["", "## 优化建议", ""]
        lines += [f"- {s}" for s in report.suggestions] or ["- 无"]
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "CODE_REVIEW_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
