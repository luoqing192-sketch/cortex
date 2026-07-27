"""JWT 认证：签发 token + FastAPI 依赖（当前用户 / 管理员校验）。"""
import time

import jwt
from fastapi import Depends, Header, HTTPException

from config import JWT_ALGORITHM, JWT_SECRET, expires_seconds


def create_token(user: dict) -> str:
    payload = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + expires_seconds(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

    return {"id": payload.get("id"), "username": payload.get("username"), "role": payload.get("role")}


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
