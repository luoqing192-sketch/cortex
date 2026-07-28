"""LangGraph 状态定义。

emit 是把事件推入 SSE 队列的 async 回调；不使用 checkpointer，故状态里放可调用对象/运行期对象无妨。
"""
from typing import Awaitable, Callable, TypedDict


class GraphState(TypedDict, total=False):
    conversation_id: int
    user_message: str
    history: list[dict]          # [{role, content, attachments?}]（已截断，含最新用户消息）
    settings: dict
    active_prompt: str
    attachments: list[dict]      # 本轮用户消息的图片附件 [{type:"image", path, url, mime, name}]
    intent: str
    full_response: str
    emit: Callable[[dict], Awaitable[None]]
