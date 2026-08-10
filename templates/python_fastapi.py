"""Python FastAPI 用户模块模板（测试层使用标准库 unittest，离线可跑）。"""

from __future__ import annotations

import re
from typing import Any


def render_python_fastapi(project: dict[str, Any]) -> dict[str, str]:
    name = project.get("module", "user")
    pkg = name.replace("-", "_")
    files: dict[str, str] = {}

    files[f"{pkg}/__init__.py"] = ""

    files[f"{pkg}/models.py"] = f'''"""数据模型（AI Coding Agent Demo 生成）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: int = 0
    username: str = ""
    password_hash: str = ""
    email: str = ""
    created_at: datetime = field(default_factory=datetime.now)


USERS: dict[str, User] = {{}}
'''

    files[f"{pkg}/schemas.py"] = f'''"""请求 / 响应结构。"""
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
'''

    files[f"{pkg}/user_service.py"] = f'''"""用户业务逻辑（纯 Python，可独立测试）。"""
from __future__ import annotations

import hashlib
import secrets

from .models import USERS, User
from .schemas import LoginRequest, LoginResponse, RegisterRequest


def _hash_password(raw: str) -> str:
    """TODO: 生产环境请替换为加盐哈希（如 bcrypt）。"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def register(request: RegisterRequest) -> User:
    if not request.username or len(request.username) < 3:
        raise ValueError("用户名长度至少 3 位")
    if not request.password or len(request.password) < 6:
        raise ValueError("密码长度至少 6 位")
    if request.username in USERS:
        raise ValueError("用户名已存在")
    user = User(
        id=len(USERS) + 1,
        username=request.username,
        password_hash=_hash_password(request.password),
        email=request.email,
    )
    USERS[request.username] = user
    return user


def login(request: LoginRequest) -> LoginResponse:
    user = USERS.get(request.username)
    if user is None or user.password_hash != _hash_password(request.password):
        raise ValueError("用户名或密码错误")
    token = secrets.token_hex(16)
    return LoginResponse(token=token, username=user.username)


def get_by_username(username: str) -> User | None:
    return USERS.get(username)
'''

    files[f"{pkg}/main.py"] = f'''"""FastAPI 入口（需要 fastapi / uvicorn 环境）。"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .schemas import LoginRequest, LoginResponse, RegisterRequest
from .user_service import get_by_username, login, register

app = FastAPI(title="{name} API", description="AI Coding Agent Demo 生成")


@app.post("/api/auth/register")
def register_api(request: RegisterRequest):
    try:
        user = register(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {{"code": 200, "message": "success", "data": user.__dict__}}


@app.post("/api/auth/login")
def login_api(request: LoginRequest) -> dict:
    try:
        resp = login(request)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return {{"code": 200, "message": "success", "data": {{"token": resp.token, "username": resp.username}}}}


@app.get("/api/users/{{username}}")
def get_user_api(username: str) -> dict:
    user = get_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {{"code": 200, "message": "success", "data": user.__dict__}}
'''

    files[f"{pkg}/test_user_service.py"] = f'''"""业务层单元测试（标准库 unittest，离线可运行）。"""
import unittest

from .schemas import LoginRequest, RegisterRequest
from .user_service import login, register


class UserServiceTest(unittest.TestCase):
    def setUp(self):
        from . import models

        models.USERS.clear()

    def test_register_success(self):
        user = register(RegisterRequest("alice", "secret123", "alice@example.com"))
        self.assertEqual(user.username, "alice")
        self.assertNotEqual(user.password_hash, "secret123")

    def test_register_duplicate(self):
        register(RegisterRequest("bob", "secret123"))
        with self.assertRaises(ValueError):
            register(RegisterRequest("bob", "secret456"))

    def test_login_success(self):
        register(RegisterRequest("alice", "secret123"))
        resp = login(LoginRequest("alice", "secret123"))
        self.assertTrue(resp.token)

    def test_login_wrong_password(self):
        register(RegisterRequest("alice", "secret123"))
        with self.assertRaises(ValueError):
            login(LoginRequest("alice", "wrong-pass"))


if __name__ == "__main__":
    unittest.main()
'''

    files[f"requirements.txt"] = f"""# 由 AI Coding Agent Demo 生成
fastapi>=0.110
uvicorn[standard]>=0.29
"""

    return files

