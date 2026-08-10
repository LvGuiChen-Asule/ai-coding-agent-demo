"""Mock Provider 使用的代码模板库。

离线模式下，MockProvider 通过这些模板模拟 LLM 的代码生成能力，
保证 Demo 在没有任何 API Key 的情况下也能跑通完整工作流。
"""

from .springboot import render_springboot, apply_captcha_to_springboot, apply_token_to_springboot
from .python_fastapi import render_python_fastapi
from .nodejs import render_nodejs

__all__ = [
    "render_springboot",
    "apply_captcha_to_springboot",
    "apply_token_to_springboot",
    "render_python_fastapi",
    "render_nodejs",
]

