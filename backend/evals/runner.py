"""跑器 —— 复用 CLI 的 LocalEngine，从事件流采集 Trajectory。

每个用例独立会话 + 独立 demo_code/{conv_id} 目录，互不污染。
"""
from __future__ import annotations

import time

from config import DEMO_CODE_DIR
from db import execute
from evals.models import Case, Trajectory


def _get_engine():
    """构造 LocalEngine（依赖 CLI 包可导入；评测在 backend venv 中，CLI 已装）。"""
    from cortex_cli.engine.local import LocalEngine

    return LocalEngine()


async def _seed_history(conversation_id: int, seed: list[dict]) -> None:
    """把预置上下文写入会话（用于多轮意图分类等场景）。"""
    for msg in seed or []:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        await execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )


async def run_case(engine, case: Case) -> Trajectory:
    conv = await engine.create_conversation(f"eval-{case.id}")
    conv_id = conv["id"]

    seed = case.input.get("seed_history")
    if seed:
        await _seed_history(conv_id, seed)

    attachments = case.input.get("attachments") or None
    events = []
    answer = ""
    start = time.perf_counter()
    try:
        async for ev in engine.stream_chat(conv_id, case.input["message"], attachments):
            events.append(ev)
            if ev.type == "content":
                answer += ev.content
    except Exception as e:  # noqa: BLE001
        return Trajectory(
            error=f"runner 异常: {e}",
            latency_ms=int((time.perf_counter() - start) * 1000),
            artifacts_dir=str(DEMO_CODE_DIR / str(conv_id)),
        )
    latency_ms = int((time.perf_counter() - start) * 1000)

    def first(etype, pick):
        for e in events:
            if e.type == etype:
                return pick(e)
        return None

    return Trajectory(
        intent=first("intent", lambda e: e.data.get("intent")),
        tool_calls=[e.data for e in events if e.type == "tool_progress"],
        sources=first("sources", lambda e: e.data.get("sources")) or [],
        preview_url=first("preview", lambda e: e.data.get("url")),
        answer=answer,
        artifacts_dir=str(DEMO_CODE_DIR / str(conv_id)),
        latency_ms=latency_ms,
        error=first("error", lambda e: e.data.get("message")),
    )
