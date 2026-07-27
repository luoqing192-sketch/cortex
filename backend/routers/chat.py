"""聊天 SSE 路由：运行 LangGraph workflow，通过 asyncio 队列桥接 SSE 事件。"""
import asyncio
import json
import math

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from auth import get_current_user
from db import execute, fetch_all, fetch_one
from graph.workflow import workflow
from llm import get_active_prompt, get_settings
from llm_queue import llm_queue
from logger import logger
from schemas import ChatBody

router = APIRouter()

MAX_HISTORY_MESSAGES = 20
MAX_CONTEXT_TOKENS = 8000

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _estimate_tokens(text: str) -> int:
    return math.ceil(len(text or "") / 3)


def _truncate(history: list[dict], base_system_tokens: int) -> list[dict]:
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]
    remaining = MAX_CONTEXT_TOKENS - base_system_tokens
    out: list[dict] = []
    for msg in reversed(history):
        t = _estimate_tokens(msg["content"])
        if remaining - t < 0 and out:
            break
        remaining -= t
        out.insert(0, msg)
    return out


@router.post("/chat")
async def chat(body: ChatBody, user: dict = Depends(get_current_user)):
    conversation_id = body.conversationId
    message = body.message

    conv = await fetch_one(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"])
    )
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 保存用户消息
    await execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, "user", message),
    )

    all_messages = await fetch_all(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    settings = await get_settings()
    active_prompt_row = await get_active_prompt()
    active_prompt = active_prompt_row["content"] if active_prompt_row else ""

    history = _truncate(all_messages, _estimate_tokens(active_prompt))

    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        try:
            status = llm_queue.get_status()
            if status["pending"] > 0:
                await emit({"type": "queue", **status})

            async def workload() -> str:
                state = {
                    "conversation_id": conversation_id,
                    "user_message": message,
                    "history": history,
                    "settings": settings,
                    "active_prompt": active_prompt,
                    "emit": emit,
                }
                result = await workflow.ainvoke(state)
                full = result.get("full_response", "") or ""

                # 保存 assistant 回复
                await execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                    (conversation_id, "assistant", full),
                )
                # 首轮自动生成标题，否则更新时间戳
                if len(all_messages) <= 1:
                    auto_title = message[:20] + "..." if len(message) > 20 else message
                    await execute(
                        "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?",
                        (auto_title, conversation_id),
                    )
                else:
                    await execute(
                        "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
                        (conversation_id,),
                    )
                return full

            await llm_queue.enqueue(workload)
        except Exception as e:  # noqa: BLE001
            logger.error("Chat error: %s", e)
            await emit({"error": "聊天失败：" + str(e)})
        finally:
            await queue.put(None)  # 结束哨兵

    task = asyncio.create_task(run())

    async def sse():
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await task

    return StreamingResponse(sse(), media_type="text/event-stream", headers=SSE_HEADERS)
