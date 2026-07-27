import time
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_current_user
from config import UPLOADS_DIR
from db import execute, fetch_all, fetch_one
from schemas import ConversationCreateBody

router = APIRouter()


@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    return await fetch_all(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", (user["id"],)
    )


@router.post("/conversations")
async def create_conversation(body: ConversationCreateBody, user: dict = Depends(get_current_user)):
    title = body.title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    new_id, _ = await execute(
        "INSERT INTO conversations (user_id, title) VALUES (?, ?)", (user["id"], title)
    )
    return await fetch_one("SELECT * FROM conversations WHERE id = ?", (new_id,))


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int, user: dict = Depends(get_current_user)):
    conv = await fetch_one(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"])
    )
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return await fetch_all(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,)
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user: dict = Depends(get_current_user)):
    await execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"])
    )
    return {"message": "对话已删除"}


@router.post("/chat/upload")
async def chat_upload(file: UploadFile = File(...), _user: dict = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有上传文件")
    unique = f"{int(time.time() * 1000)}-{file.filename}"
    dest = UPLOADS_DIR / unique
    data = await file.read()
    dest.write_bytes(data)
    return {
        "message": "文件上传成功",
        "file": {
            "id": int(time.time() * 1000),
            "filename": unique,
            "original_name": file.filename,
            "size": len(data),
            "path": str(dest),
        },
    }
