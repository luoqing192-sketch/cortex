"""聊天 SSE 路由：运行 LangGraph workflow，通过 asyncio 队列桥接 SSE 事件。

workflow 驱动逻辑抽到 chat_runner.run_chat_workflow（与 CLI LocalEngine 共用）；
本路由只负责：鉴权 + 队列 + 把 emit 的事件转成 SSE 帧下发。
"""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from auth import get_current_user
from chat_runner import run_chat_workflow, verify_conversation
from llm_queue import llm_queue
from logger import logger
from schemas import ChatBody

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/chat")
async def chat(body: ChatBody, user: dict = Depends(get_current_user)):
    if not await verify_conversation(body.conversationId, user["id"]):
        raise HTTPException(status_code=404, detail="对话不存在")

    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        try:
            status = llm_queue.get_status()
            if status["pending"] > 0:
                await emit({"type": "queue", **status})

            async def workload():
                return await run_chat_workflow(
                    body.conversationId, body.message, emit,
                    attachments=body.attachments,
                )

            await llm_queue.enqueue(workload)
        except Exception as e:  # noqa: BLE001
            logger.error("Chat error: %s", e)
            await emit({"error": "聊天失败：" + str(e)})
        finally:
            await queue.put(None)

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
