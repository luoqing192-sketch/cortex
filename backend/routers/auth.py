import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from auth import create_token, get_current_user
from db import fetch_one
from schemas import LoginBody

router = APIRouter()


@router.post("/auth/login")
async def login(body: LoginBody):
    user = await fetch_one("SELECT * FROM users WHERE username = ?", (body.username,))
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    ok = bcrypt.checkpw(body.password.encode(), user["password_hash"].encode())
    if not ok:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(user)
    return {"token": token, "user": {"id": user["id"], "username": user["username"], "role": user["role"]}}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    row = await fetch_one(
        "SELECT id, username, role, created_at FROM users WHERE id = ?", (user["id"],)
    )
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return row
