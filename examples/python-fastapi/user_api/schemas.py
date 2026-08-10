"""请求 / 响应结构。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RegisterRequest:
    username: str
    password: str
    email: str = ""


@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class LoginResponse:
    token: str
    username: str
    message: str = "登录成功"
