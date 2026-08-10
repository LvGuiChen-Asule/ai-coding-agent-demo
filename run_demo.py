#!/usr/bin/env python3
"""AI Coding Agent Demo 命令行入口。

用法示例：
  python run_demo.py "帮我创建一个SpringBoot用户登录模块"
  python run_demo.py "创建一个Python FastAPI用户接口" --stack python
  python run_demo.py "修改登录逻辑，增加验证码校验" --modify --workspace demo_output
  python run_demo.py --provider openai
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agent_core import AgentWorkflow, create_provider
from agent_core.config import settings, load_dotenv


STAGE_COLORS = {
    "start": "\033[36m",
    "plan": "\033[34m",
    "codegen": "\033[32m",
    "fileop": "\033[33m",
    "modify": "\033[33m",
    "test": "\033[35m",
    "fix": "\033[31m",
    "reflect": "\033[96m",
    "done": "\033[92m",
}


def colorize(text: str, color: str) -> str:
    if os.name == "nt" or not sys.stdout.isatty():
        return text
    return f"{color}{text}\033[0m"


def print_events(events: list[dict]) -> None:
    for event in events:
        color = STAGE_COLORS.get(event["stage"], "")
        tag = f"[{event['stage'].upper()}]"
        print(colorize(f"{tag:<10} {event['agent']:<18} {event['message']}", color))


def print_summary(result: dict) -> None:
    print("\n" + "=" * 72)
    print("工作流执行结果")
    print("=" * 72)
    print(f"需求    : {result['requirement']}")
    print(f"Provider: {result['provider']}")
    print(f"生成文件: {len(result['generated_files'])} 个")
    print(f"工作区  : {result['workspace']}")
    test = result.get("test_report") or {}
    if test:
        status = "✅ 通过" if test.get("ok") else "❌ 失败"
        print(f"测试    : {status} — {test.get('summary', '')}")
    review = result.get("review_report") or {}
    if review:
        print(f"评分    : {review.get('score')}/100，问题 {len(review.get('issues', []))} 个")
        for issue in review.get("issues", [])[:5]:
            print(
                f"  ⚠ [{issue['severity']}] {issue['file']}: {issue['title']} "
                f"→ {issue['suggestion']}"
            )
    print("=" * 72)


def main() -> None:
    # Windows 控制台默认 GBK，统一切到 UTF-8，避免中文 / emoji 报错
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="AI Coding Agent Demo — 模拟 AI 软件工程师工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "requirement",
        nargs="?",
        default="帮我创建一个SpringBoot用户登录模块",
        help="自然语言需求（默认：SpringBoot 用户登录模块）",
    )
    parser.add_argument("--stack", choices=["springboot", "python", "node"], default=None)
    parser.add_argument("--provider", choices=["mock", "openai", "qwen"], default=settings.llm_provider)
    parser.add_argument("--workspace", default=settings.workspace_root, help="生成代码的输出目录")
    parser.add_argument("--modify", action="store_true", help="对已有项目执行修改流程")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON 结果")
    parser.add_argument("--max-fix-iterations", type=int, default=settings.max_fix_iterations)
    parser.add_argument(
        "--demo-bug",
        action="store_true",
        help="Demo 专用：注入确定性 Bug 触发测试失败，展示自动修复闭环",
    )
    args = parser.parse_args()

    requirement = args.requirement
    if args.modify and not any(k in requirement for k in ("修改", "优化", "增加", "添加")):
        requirement = "修改登录逻辑，增加验证码校验"

    provider = create_provider(args.provider)
    workflow = AgentWorkflow(
        provider=provider,
        workspace=args.workspace,
        max_fix_iterations=args.max_fix_iterations,
        demo_bug=args.demo_bug,
    )
    result = workflow.run(requirement, stack=args.stack)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    print_events([e.to_dict() for e in result.events])
    print_summary(result.to_dict())

    tree = workflow.project_tree()
    print("\n生成的项目结构：")
    for entry in tree:
        indent = "  " * (entry["path"].count("/"))
        icon = "📁" if entry["type"] == "dir" else "📄"
        size = f" ({entry['size']}B)" if entry["type"] == "file" else ""
        print(f"{indent}{icon} {entry['path']}{size}")


if __name__ == "__main__":
    main()
