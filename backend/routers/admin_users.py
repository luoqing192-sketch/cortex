import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin
from db import execute, fetch_all, fetch_one
from schemas import CreateUserBody, PasswordBody

router = APIRouter()


@router.get("/admin/users")
async def list_users(_admin: dict = Depends(require_admin)):
    return await fetch_all(
        "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC"
    )


@router.post("/admin/users")
async def create_user(body: CreateUserBody, _admin: dict = Depends(require_admin)):
    existing = await fetch_one("SELECT id FROM users WHERE username = ?", (body.username,))
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt(rounds=10)).decode()
    new_id, _ = await execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (body.username, pw_hash, body.role),
    )
    return {"id": new_id, "username": body.username, "role": body.role}


@router.put("/admin/users/{user_id}/password")
async def reset_password(user_id: int, body: PasswordBody, _admin: dict = Depends(require_admin)):
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt(rounds=10)).decode()
    await execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id))
    return {"message": "密码已更新"}


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")
    await execute("DELETE FROM users WHERE id = ?", (user_id,))
    return {"message": "用户已删除"}
