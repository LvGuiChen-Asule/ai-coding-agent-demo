"""数据模型（AI Coding Agent Demo 生成）。"""
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


USERS: dict[str, User] = {}
