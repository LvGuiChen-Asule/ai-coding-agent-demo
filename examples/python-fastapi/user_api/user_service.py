"""用户业务逻辑（纯 Python，可独立测试）。"""
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
