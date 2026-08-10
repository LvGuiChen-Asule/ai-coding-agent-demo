"""FastAPI 入口（需要 fastapi / uvicorn 环境）。"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .schemas import LoginRequest, LoginResponse, RegisterRequest
from .user_service import get_by_username, login, register

app = FastAPI(title="user-api API", description="AI Coding Agent Demo 生成")


@app.post("/api/auth/register")
def register_api(request: RegisterRequest):
    try:
        user = register(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"code": 200, "message": "success", "data": user.__dict__}


@app.post("/api/auth/login")
def login_api(request: LoginRequest) -> dict:
    try:
        resp = login(request)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return {"code": 200, "message": "success", "data": {"token": resp.token, "username": resp.username}}


@app.get("/api/users/{username}")
def get_user_api(username: str) -> dict:
    user = get_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "success", "data": user.__dict__}
