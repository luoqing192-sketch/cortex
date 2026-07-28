"""LocalEngine：进程内直接跑 backend 的 LangGraph workflow（离线，无需 HTTP/JWT/队列）。

依赖 backend 可 import（pip install -e backend/）。会话/持久化仍走 backend.db 的同一 SQLite，
故 local 建的会话 remote 也能看到。
"""
from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from cortex_cli.engine.base import Engine, EngineError
from cortex_cli.events import ChatEvent

LOCAL_USER = {"id": 1, "username": "admin", "role": "admin"}


class LocalEngine(Engine):
    def __init__(self):
        try:
            import db  # noqa: F401  # 触发 backend 可导入性检查
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "无法导入 backend，请先安装：pip install -e backend/（或 cli[local]）"
            ) from e
        self._inited = False

    async def _ensure_init(self):
        if not self._inited:
            import db

            await db.init_db()
            await db.ensure_admin()
            self._inited = True

    async def stream_chat(
        self, conversation_id: int, message: str, attachments: list[dict] | None = None
    ) -> AsyncIterator[ChatEvent]:
        await self._ensure_init()
        from chat_runner import run_chat_workflow, verify_conversation

        if not await verify_conversation(conversation_id, LOCAL_USER["id"]):
            raise EngineError(f"会话 {conversation_id} 不存在")

        queue: asyncio.Queue = asyncio.Queue()

        async def emit(event: dict):
            await queue.put(event)

        async def run():
            try:
                await run_chat_workflow(conversation_id, message, emit, attachments=attachments)
            except Exception as e:  # noqa: BLE001
                await emit({"error": "聊天失败：" + str(e)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield ChatEvent.from_sse(event)
            yield ChatEvent(type="done")
        finally:
            await task

    async def create_conversation(self, title: str | None = None) -> dict:
        await self._ensure_init()
        import db

        t = title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        new_id, _ = await db.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)", (LOCAL_USER["id"], t)
        )
        return await db.fetch_one("SELECT * FROM conversations WHERE id = ?", (new_id,))

    async def list_conversations(self) -> list[dict]:
        await self._ensure_init()
        import db

        return await db.fetch_all(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (LOCAL_USER["id"],),
        )

    async def delete_conversation(self, conversation_id: int) -> None:
        await self._ensure_init()
        import db

        await db.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, LOCAL_USER["id"]),
        )

    async def whoami(self) -> dict | None:
        return LOCAL_USER

    async def upload_image(self, path: str) -> dict:
        """local 模式无需上传，直接引用本地路径（backend.media 读盘编码）。"""
        p = Path(path)
        if not p.exists():
            raise EngineError(f"文件不存在: {path}")
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return {"type": "image", "name": p.name, "path": str(p.resolve()), "url": None, "mime": mime}
