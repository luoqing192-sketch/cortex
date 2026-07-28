"""RemoteEngine：连后端 /api + SSE。把后端 SSE 事件翻译成 ChatEvent。"""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import AsyncIterator

import httpx

from cortex_cli.engine.base import AuthError, Engine, EngineError
from cortex_cli.events import ChatEvent


class RemoteEngine(Engine):
    def __init__(self, api_url: str, token: str | None):
        self.api_url = api_url.rstrip("/")
        self.token = token

    def _headers(self, extra: dict | None = None) -> dict:
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def _client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.api_url, headers=self._headers(), timeout=timeout)

    @staticmethod
    def _raise_for_auth(resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise AuthError("未登录或 token 失效，请先 `cortex login`")

    async def stream_chat(
        self, conversation_id: int, message: str, attachments: list[dict] | None = None
    ) -> AsyncIterator[ChatEvent]:
        body = {"conversationId": conversation_id, "message": message}
        if attachments:
            body["attachments"] = attachments
        try:
            async with httpx.AsyncClient(
                base_url=self.api_url, headers=self._headers(), timeout=None
            ) as client:
                async with client.stream("POST", "/api/chat", json=body) as resp:
                    if resp.status_code in (401, 403):
                        raise AuthError("未登录或 token 失效，请先 `cortex login`")
                    if resp.status_code >= 400:
                        text = (await resp.aread()).decode("utf-8", "ignore")
                        raise EngineError(f"请求失败 {resp.status_code}: {text[:200]}")
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            yield ChatEvent(type="done")
                            return
                        try:
                            obj = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        yield ChatEvent.from_sse(obj)
                yield ChatEvent(type="done")
        except (httpx.ConnectError, httpx.ReadError) as e:
            raise EngineError(f"无法连接后端 {self.api_url}（后端是否已启动？）：{e}")

    async def create_conversation(self, title: str | None = None) -> dict:
        async with self._client() as client:
            resp = await client.post("/api/conversations", json={"title": title})
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def list_conversations(self) -> list[dict]:
        async with self._client() as client:
            resp = await client.get("/api/conversations")
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def delete_conversation(self, conversation_id: int) -> None:
        async with self._client() as client:
            resp = await client.delete(f"/api/conversations/{conversation_id}")
            self._raise_for_auth(resp)
            resp.raise_for_status()

    async def whoami(self) -> dict | None:
        async with self._client() as client:
            resp = await client.get("/api/auth/me")
            if resp.status_code in (401, 403):
                return None
            resp.raise_for_status()
            return resp.json()

    async def upload_image(self, path: str) -> dict:
        p = Path(path)
        if not p.exists():
            raise EngineError(f"文件不存在: {path}")
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        async with self._client(timeout=60.0) as client:
            with open(p, "rb") as f:
                files = {"file": (p.name, f, mime)}
                resp = await client.post("/api/chat/upload", files=files)
            self._raise_for_auth(resp)
            resp.raise_for_status()
            info = resp.json().get("file", {})
            return {
                "type": "image",
                "name": info.get("original_name") or p.name,
                "path": info.get("path"),
                "url": info.get("url"),
                "mime": mime,
            }

    async def login(self, username: str, password: str) -> dict:
        """返回 {token, user}。"""
        async with self._client() as client:
            resp = await client.post(
                "/api/auth/login", json={"username": username, "password": password}
            )
            if resp.status_code == 401:
                raise AuthError("用户名或密码错误")
            resp.raise_for_status()
            return resp.json()
