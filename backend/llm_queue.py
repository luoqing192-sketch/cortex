"""LLM 请求队列：asyncio 信号量并发控制 + 入队等待超时。

对齐原 llm-queue.js 语义：超时只作用于「在队列中等待槽位」阶段，
一旦拿到槽位开始执行（可能是长时间流式），不再受超时限制。
"""
import asyncio
from typing import Awaitable, Callable, TypeVar

from config import LLM_MAX_CONCURRENT, LLM_REQUEST_TIMEOUT

T = TypeVar("T")


class LLMQueue:
    def __init__(self, max_concurrent: int, timeout: int):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._sem = asyncio.Semaphore(max_concurrent)
        self.active = 0
        self.pending = 0

    async def enqueue(self, fn: Callable[[], Awaitable[T]]) -> T:
        self.pending += 1
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=self.timeout)
        except asyncio.TimeoutError:
            self.pending -= 1
            raise RuntimeError("Request timeout in queue")

        self.pending -= 1
        self.active += 1
        try:
            return await fn()
        finally:
            self.active -= 1
            self._sem.release()

    def get_status(self) -> dict:
        return {
            "pending": self.pending,
            "active": self.active,
            "maxConcurrent": self.max_concurrent,
            "estimatedWaitTime": self.pending * 5000,
        }


llm_queue = LLMQueue(LLM_MAX_CONCURRENT, LLM_REQUEST_TIMEOUT)
