import time

from fastapi import APIRouter

router = APIRouter()

_START = time.time()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "uptime": time.time() - _START,
    }
