"""聊天工作流驱动 —— routers/chat.py（remote SSE）与 CLI LocalEngine 共用。

职责：加载历史 + Token 截断 → 保存用户消息 → 跑 LangGraph workflow（通过 emit 推事件）
     → 保存 assistant 回复 → 首轮生成标题 / 更新时间戳。

调用方只需提供一个 async `emit(event: dict)` 回调即可拿到与 SSE 完全一致的事件流。
"""
from __future__ import annotations

import math
from typing import Awaitable, Callable

from db import execute, fetch_all, fetch_one
from graph.workflow import workflow
from llm import get_active_prompt, get_settings
from logger import logger

MAX_HISTORY_MESSAGES = 20
MAX_CONTEXT_TOKENS = 8000

Emit = Callable[[dict], Awaitable[None]]


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


async def verify_conversation(conversation_id: int, user_id: int) -> bool:
    row = await fetch_one(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    return row is not None


async def run_chat_workflow(
    conversation_id: int,
    message: str,
    emit: Emit,
    *,
    attachments: list[dict] | None = None,
) -> str:
    """跑一轮对话。假定 conversation 归属已校验。返回 assistant 完整回复文本。"""
    import json

    # 保存用户消息（含附件）
    await execute(
        "INSERT INTO messages (conversation_id, role, content, attachments) VALUES (?, ?, ?, ?)",
        (conversation_id, "user", message, json.dumps(attachments, ensure_ascii=False) if attachments else None),
    )

    all_messages = await fetch_all(
        "SELECT role, content, attachments FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    settings = await get_settings()
    active_prompt_row = await get_active_prompt()
    active_prompt = active_prompt_row["content"] if active_prompt_row else ""

    history = _truncate(all_messages, _estimate_tokens(active_prompt))

    state = {
        "conversation_id": conversation_id,
        "user_message": message,
        "history": history,
        "settings": settings,
        "active_prompt": active_prompt,
        "attachments": attachments or [],
        "emit": emit,
    }
    result = await workflow.ainvoke(state)
    full = result.get("full_response", "") or ""

    await execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, "assistant", full),
    )
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
    logger.info("[chat] 完成 conv=%s，回复 %d 字符", conversation_id, len(full))
    return full
