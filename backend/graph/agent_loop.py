"""tool-call 循环与流式输出的共享骨架，供 generate_page / web_research 复用。"""
import json
from typing import Awaitable, Callable

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from media import build_multimodal_content

Emit = Callable[[dict], Awaitable[None]]


def _parse_attachments(raw) -> list[dict]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw) or []
    except (json.JSONDecodeError, TypeError):
        return []


def to_lc_messages(system: str, history: list[dict]) -> list:
    """构造 LangChain 消息。带图片附件的 user 消息会转成多模态 content blocks。"""
    msgs: list = [SystemMessage(content=system)]
    for m in history:
        role, content = m.get("role"), m.get("content") or ""
        if role == "user":
            attachments = _parse_attachments(m.get("attachments"))
            msgs.append(HumanMessage(content=build_multimodal_content(content, attachments)))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
        elif role == "system":
            msgs.append(SystemMessage(content=content))
    return msgs


def _chunk_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                parts.append(p.get("text") or p.get("content") or "")
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return ""


async def run_tool_loop(
    chat_with_tools,
    messages: list,
    execute_fn: Callable[[str, dict], dict],
    emit: Emit,
    *,
    max_iters: int = 10,
    on_tool: Callable[[str, dict, dict], None] | None = None,
) -> list:
    """反复让模型调用工具，直到不再产生 tool_calls 或到达 max_iters。返回追加后的 messages。"""
    iters = 0
    while iters < max_iters:
        iters += 1
        ai: AIMessage = await chat_with_tools.ainvoke(messages)
        messages.append(ai)
        tool_calls = ai.tool_calls or []
        if not tool_calls:
            break
        for tc in tool_calls:
            name = tc.get("name")
            args = tc.get("args") or {}
            tc_id = tc.get("id")
            await emit({"type": "tool_progress", "tool": name, "status": "running"})
            try:
                result = execute_fn(name, args)
                status = "completed"
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e)}
                status = "error"
            if on_tool:
                try:
                    on_tool(name, args, result)
                except Exception:  # noqa: BLE001
                    pass
            messages.append(
                ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=tc_id)
            )
            await emit({"type": "tool_progress", "tool": name, "status": status})
    return messages


async def stream_final(chat, messages: list, emit: Emit) -> str:
    """无工具的流式回答，逐块 emit {content}，返回完整文本。"""
    full = ""
    async for chunk in chat.astream(messages):
        text = _chunk_text(getattr(chunk, "content", ""))
        if text:
            full += text
            await emit({"content": text})
    return full
