from fastapi import APIRouter, Depends

from auth import get_current_user
from llm_queue import llm_queue

router = APIRouter()


@router.get("/queue/status")
async def queue_status(_user: dict = Depends(get_current_user)):
    return llm_queue.get_status()
