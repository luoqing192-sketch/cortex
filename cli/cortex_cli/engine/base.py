"""Engine 抽象 —— CLI 命令层只面向它编程，remote/local 各实现一份。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from cortex_cli.events import ChatEvent


class AuthError(Exception):
    """需要登录 / token 失效。"""


class EngineError(Exception):
    """连接失败等运行期错误。"""


class Engine(ABC):
    @abstractmethod
    def stream_chat(
        self,
        conversation_id: int,
        message: str,
        attachments: list[dict] | None = None,
    ) -> AsyncIterator[ChatEvent]:
        """流式对话，逐事件产出。attachments: [{path|url, mime, name}]。"""
        ...

    @abstractmethod
    async def create_conversation(self, title: str | None = None) -> dict: ...

    @abstractmethod
    async def list_conversations(self) -> list[dict]: ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: int) -> None: ...

    @abstractmethod
    async def whoami(self) -> dict | None: ...

    async def upload_image(self, path: str) -> dict:
        """上传图片，返回引用 {path, url, name, mime}。默认不支持。"""
        raise NotImplementedError

    async def close(self) -> None:  # 可选清理
        pass
