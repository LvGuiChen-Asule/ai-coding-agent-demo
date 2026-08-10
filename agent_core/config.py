"""运行配置：读取环境变量与 .env 文件（轻量实现，无 python-dotenv 依赖）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_dotenv(path: Optional[str] = None) -> None:
    """读取 .env 文件到环境变量（不覆盖已存在的环境变量）。"""
    env_path = Path(path or ".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


class Settings:
    """集中管理项目配置。"""

    def __init__(self) -> None:
        load_dotenv()
        self.llm_provider: str = get_env("LLM_PROVIDER", "mock").lower()
        self.openai_api_key: str = get_env("OPENAI_API_KEY")
        self.openai_base_url: str = get_env("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.openai_model: str = get_env("OPENAI_MODEL", "gpt-4o-mini")
        self.qwen_api_key: str = get_env("QWEN_API_KEY")
        self.qwen_base_url: str = get_env(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.qwen_model: str = get_env("QWEN_MODEL", "qwen-plus")
        self.workspace_root: str = get_env("WORKSPACE_ROOT", "./demo_output")
        self.max_fix_iterations: int = int(get_env("MAX_FIX_ITERATIONS", "3"))
        self.server_port: int = int(get_env("SERVER_PORT", "8000"))


settings = Settings()

