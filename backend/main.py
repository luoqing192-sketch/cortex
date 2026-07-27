"""Cortex 后端入口（FastAPI）。

挂载：/api/* 路由、/preview 代码预览静态、前端 dist 静态 + SPA fallback。
"""
import logger as _logger  # noqa: F401  # 初始化日志（副作用）
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from config import DEMO_CODE_DIR, FRONTEND_DIST
from db import close_conn, init_db
from init_admin import ensure_admin_user
from logger import logger
from routers import (
    admin_prompts,
    admin_settings,
    admin_users,
    admin_wiki,
    auth as auth_router,
    chat,
    conversations,
    health,
    queue as queue_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_admin_user()
    logger.info("🚀 Cortex backend 启动完成")
    yield
    await close_conn()


app = FastAPI(title="Cortex", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- API 路由（统一 /api 前缀）----
for r in (
    health.router,
    queue_router.router,
    auth_router.router,
    admin_users.router,
    admin_settings.router,
    admin_prompts.router,
    admin_wiki.router,
    conversations.router,
    chat.router,
):
    app.include_router(r, prefix="/api")


# ---- 代码预览静态服务（带同源框架头）----
class PreviewStatic(StaticFiles):
    def is_not_modified(self, *args, **kwargs):  # noqa: D401
        return super().is_not_modified(*args, **kwargs)


DEMO_CODE_DIR.mkdir(parents=True, exist_ok=True)
preview_app = StaticFiles(directory=str(DEMO_CODE_DIR), html=True)


@app.middleware("http")
async def add_preview_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/preview"):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
    return response


app.mount("/preview", preview_app, name="preview")

# ---- 前端静态资源 ----
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
else:
    logger.warning("⚠️ 前端未构建：cd frontend && npm install && npm run build")


# ---- SPA fallback（非 /api、非 /preview 的 HTML 请求返回 index.html）----
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith(("api/", "preview/")):
        return JSONResponse({"error": "Not found"}, status_code=404)
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        # 具体静态文件优先返回
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(index))
    return JSONResponse(
        {"error": "Frontend not built. Run: cd frontend && npm install && npm run build"},
        status_code=503,
    )


if __name__ == "__main__":
    import uvicorn

    from config import PORT

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
