"""LLM Provider 层。

提供统一的 Chat / JSON 输出接口：
- OpenAIProvider：OpenAI Chat Completions
- QwenProvider：通义千问（DashScope 兼容模式）
- MockProvider：离线模拟，无需 API Key，演示完整工作流
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Optional

from .config import settings


def extract_json(text: str) -> Any:
    """从 LLM 返回文本中鲁棒地提取 JSON。

    支持：纯 JSON、markdown 代码块包裹、前后附带思考过程文本。
    """
    if not text:
        raise ValueError("LLM 返回为空，无法解析 JSON")

    # 1) 去掉 markdown 代码块围栏
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)

    # 2) 找到第一个 { 或 [ 开始，做括号配对提取
    start = None
    for idx, ch in enumerate(text):
        if ch in "{[":
            start = idx
            break
    if start is None:
        raise ValueError(f"文本中未找到 JSON：{text[:200]}")

    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return json.loads(text[start : idx + 1])
    raise ValueError(f"JSON 括号未闭合：{text[:200]}")


class BaseLLMProvider:
    """LLM Provider 抽象基类。"""

    name: str = "base"

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        raise NotImplementedError

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        return self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Any:
        return extract_json(self.chat(messages, temperature=temperature, max_tokens=max_tokens))

    def complete_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Any:
        return extract_json(
            self.complete(system, user, temperature=temperature, max_tokens=max_tokens)
        )


class _OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI / 通义千问共用兼容实现（标准库 urllib，无需第三方 SDK）。"""

    name = "compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = ""

    def _endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        if not self.api_key:
            raise RuntimeError(
                f"Provider {self.name} 未配置 API Key。"
                "请设置环境变量，或使用 LLM_PROVIDER=mock 离线演示。"
            )
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            self._endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API 请求失败 HTTP {exc.code}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM API 网络错误: {exc.reason}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"LLM API 返回格式异常: {str(data)[:500]}") from exc


class OpenAIProvider(_OpenAICompatibleProvider):
    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model


class QwenProvider(_OpenAICompatibleProvider):
    name = "qwen"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.qwen_api_key
        self.base_url = base_url or settings.qwen_base_url
        self.model = model or settings.qwen_model


class MockProvider(BaseLLMProvider):
    """离线 Mock Provider。

    通过识别 system prompt 中的角色关键词，模拟 Planner / Coder /
    Patcher / Reviewer 的推理与结构化输出，让 Demo 无需任何 API Key
    即可跑通完整 Agent 工作流。
    """

    name = "mock"

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        payload = self._dispatch(system, user)
        reasoning = payload.pop("_reasoning", None)
        output = json.dumps(payload, ensure_ascii=False, indent=2)
        if reasoning:
            return f"[思考过程]\n{reasoning}\n\n[结构化输出]\n```json\n{output}\n```"
        return output

    # ------------------------------------------------------------------

    def _dispatch(self, system: str, user: str) -> dict[str, Any]:
        # 1) 优先按显式 Agent 标识路由，避免关键词歧义
        marker_map = {
            "PLANNER": self._mock_plan,
            "CODE_GENERATOR": self._mock_generate,
            "FILE_PATCHER": self._mock_modify,
            "TESTER": lambda u: {"test_plan": "auto"},
            "REVIEWER": self._mock_review,
            "FIXER": self._mock_fix,
        }
        for marker, handler in marker_map.items():
            if f"【Agent 标识】{marker}" in system:
                return handler(user)

        # 2) 兜底：关键词路由（审查优先于修改，避免「修改建议」误判）
        if "规划" in system or "planner" in system.lower():
            return self._mock_plan(user)
        if "代码生成" in system or "coder" in system.lower():
            return self._mock_generate(user)
        if "代码审查" in system or "review" in system.lower() or "reflection" in system.lower():
            return self._mock_review(user)
        if "修改" in system or "patch" in system.lower():
            return self._mock_modify(user)
        if "修复" in system or "fix" in system.lower():
            return self._mock_fix(user)
        return {"reply": f"MockProvider 收到消息：{user[:100]}"}

    @staticmethod
    def _mock_plan(user: str) -> dict[str, Any]:
        from .planner import mock_plan

        data = json.loads(user)
        plan = mock_plan(data.get("requirement", ""), data.get("stack", ""))
        return {
            "_reasoning": "用户需求为「%s」。\n"
            "第一步：识别技术栈关键词并抽取项目名。\n"
            "第二步：按 创建工程 -> 实体/DTO -> 数据访问 -> 业务逻辑 -> 接口 -> SQL -> 测试 的依赖顺序拆解任务。\n"
            "第三步：为每个步骤指定目标文件，便于后续 Agent 精准操作。"
            % data.get("requirement", ""),
            "task": plan["task"],
            "stack": plan["stack"],
            "steps": plan["steps"],
        }

    @staticmethod
    def _mock_generate(user: str) -> dict[str, Any]:
        from .coder import mock_generate

        data = json.loads(user)
        files = mock_generate(
            requirement=data.get("requirement", ""),
            step=data.get("step", {}),
            project=data.get("project", {}),
        )
        return {
            "_reasoning": "根据任务步骤「%s」生成代码：\n"
            "- 遵循对应技术栈的工程规范与分层结构；\n"
            "- 为每个文件补充中文注释与类说明；\n"
            "- 输出结构化文件列表，交由 File Operation Agent 落盘。"
            % data.get("step", {}).get("title", ""),
            "files": [{"path": k, "content": v} for k, v in files.items()],
        }

    @staticmethod
    def _mock_modify(user: str) -> dict[str, Any]:
        from .coder import mock_modify

        data = json.loads(user)
        files = mock_modify(
            requirement=data.get("requirement", ""),
            project=data.get("project", {}),
            existing_files=data.get("existing_files", {}),
        )
        return {
            "_reasoning": "检测到修改需求，先读取目标文件，"
            "定位需要变更的方法与字段，再输出修改后的完整文件内容，"
            "由 FileWriter 以 diff 方式落盘。",
            "files": [{"path": k, "content": v} for k, v in files.items()],
        }

    @staticmethod
    def _mock_review(user: str) -> dict[str, Any]:
        from .reflector import mock_review

        data = json.loads(user)
        return mock_review(data.get("files", {}))

    @staticmethod
    def _mock_fix(user: str) -> dict[str, Any]:
        data = json.loads(user)
        errors = data.get("errors", [])
        suggestion = "修复思路：\n"
        for err in errors[:3]:
            suggestion += f"- 定位「{err.get('file', '?')}」中与「{err.get('detail', '?')}」相关的代码，\n"
        suggestion += "- 补充判空与边界校验，重新生成后再次运行测试验证。"
        return {
            "_reasoning": "根据测试失败信息分析根因，输出修复建议与涉及文件。",
            "fix_summary": suggestion,
            "target_files": data.get("target_files", []),
        }


def create_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """按名称创建 LLM Provider。"""
    provider = (name or settings.llm_provider).lower()
    if provider == "mock":
        return MockProvider()
    if provider == "openai":
        return OpenAIProvider()
    if provider in ("qwen", "dashscope", "tongyi"):
        return QwenProvider()
    raise ValueError(f"未知 LLM Provider: {provider}（可选：mock / openai / qwen）")
