from fastapi import APIRouter, Depends

from auth import require_admin
from db import execute, fetch_all, fetch_one
from schemas import PromptBody, PromptTestBody

router = APIRouter()


def _normalize(row: dict | None) -> dict | None:
    if row is None:
        return None
    row = dict(row)
    row["is_active"] = bool(row.get("is_active"))
    return row


@router.get("/admin/prompts")
async def list_prompts(_admin: dict = Depends(require_admin)):
    rows = await fetch_all("SELECT * FROM prompts ORDER BY is_active DESC, created_at DESC")
    return [_normalize(r) for r in rows]


@router.get("/admin/prompts/active")
async def active_prompt(_admin: dict = Depends(require_admin)):
    return _normalize(await fetch_one("SELECT * FROM prompts WHERE is_active = 1 LIMIT 1"))


@router.post("/admin/prompts")
async def create_prompt(body: PromptBody, _admin: dict = Depends(require_admin)):
    is_active = 1 if body.is_active else 0
    if is_active:
        await execute("UPDATE prompts SET is_active = 0")
    new_id, _ = await execute(
        "INSERT INTO prompts (name, content, description, is_active) VALUES (?, ?, ?, ?)",
        (body.name, body.content, body.description or "", is_active),
    )
    return _normalize(await fetch_one("SELECT * FROM prompts WHERE id = ?", (new_id,)))


@router.put("/admin/prompts/{prompt_id}")
async def update_prompt(prompt_id: int, body: PromptBody, _admin: dict = Depends(require_admin)):
    is_active = 1 if body.is_active else 0
    if is_active:
        await execute("UPDATE prompts SET is_active = 0 WHERE id != ?", (prompt_id,))
    await execute(
        "UPDATE prompts SET name = ?, content = ?, description = ?, is_active = ?, "
        "updated_at = datetime('now') WHERE id = ?",
        (body.name, body.content, body.description, is_active, prompt_id),
    )
    return _normalize(await fetch_one("SELECT * FROM prompts WHERE id = ?", (prompt_id,)))


@router.delete("/admin/prompts/{prompt_id}")
async def delete_prompt(prompt_id: int, _admin: dict = Depends(require_admin)):
    await execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    return {"message": "提示词已删除"}


@router.post("/admin/prompts/{prompt_id}/activate")
async def activate_prompt(prompt_id: int, _admin: dict = Depends(require_admin)):
    await execute("UPDATE prompts SET is_active = 0")
    await execute("UPDATE prompts SET is_active = 1 WHERE id = ?", (prompt_id,))
    return {"message": "提示词已激活"}


@router.post("/admin/prompts/{prompt_id}/deactivate")
async def deactivate_prompt(prompt_id: int, _admin: dict = Depends(require_admin)):
    await execute("UPDATE prompts SET is_active = 0 WHERE id = ?", (prompt_id,))
    return {"message": "提示词已停用"}


@router.post("/admin/prompts/test")
async def test_prompt(body: PromptTestBody, _admin: dict = Depends(require_admin)):
    """流式测试 prompt。复用 chat 的 SSE 输出格式。"""
    from fastapi.responses import StreamingResponse

    from llm import build_chat, get_settings

    async def gen():
        try:
            settings = await get_settings()
            chat = build_chat(settings, streaming=True)
            messages = [
                {"role": "system", "content": body.promptContent},
                {"role": "user", "content": body.testMessage},
            ]
            import json

            async for chunk in chat.astream(messages):
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:  # noqa: BLE001
            import json

            yield f"data: {json.dumps({'error': '测试失败：' + str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
