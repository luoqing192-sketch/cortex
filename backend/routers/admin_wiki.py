import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_current_user, require_admin
from config import WIKI_DIR
from llm import get_settings
from logger import logger
from schemas import WikiOrganizeBody, WikiQueryBody
from wiki_service import run_wiki_organize, run_wiki_query

router = APIRouter()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


@router.get("/admin/wiki")
async def list_wiki(_user: dict = Depends(get_current_user)):
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for p in WIKI_DIR.glob("*.md"):
        if not p.is_file():
            continue
        stat = p.stat()
        files.append(
            {
                "name": p.stem,
                "filename": p.name,
                "size": stat.st_size,
                "updated_at": _iso(stat.st_mtime),
            }
        )
    files.sort(key=lambda f: f["updated_at"], reverse=True)
    return files


@router.post("/admin/wiki/upload")
async def upload_wiki(file: UploadFile = File(...), _admin: dict = Depends(require_admin)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有上传文件")
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    target_name = file.filename if file.filename.endswith(".md") else file.filename + ".md"
    target = WIKI_DIR / target_name
    target.write_bytes(await file.read())
    stat = target.stat()
    logger.info("[wiki upload] 文件: %s | 大小: %s", target_name, stat.st_size)
    return {
        "message": "Wiki 文件上传成功",
        "file": {
            "name": target.stem,
            "filename": target_name,
            "size": stat.st_size,
            "updated_at": _iso(stat.st_mtime),
        },
    }


@router.delete("/admin/wiki/{filename}")
async def delete_wiki(filename: str, _admin: dict = Depends(require_admin)):
    filename = urllib.parse.unquote(filename)
    target_name = filename if filename.endswith(".md") else filename + ".md"
    target = WIKI_DIR / target_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    target.unlink()
    return {"message": "Wiki 文件已删除"}


@router.post("/admin/wiki/organize")
async def organize_wiki(body: WikiOrganizeBody, _admin: dict = Depends(require_admin)):
    task = body.task or "扫描本目录所有 markdown 文档，按主题分类生成 INDEX.md，每个文档配 1 行中文摘要。"
    try:
        settings = await get_settings()
        logger.info("[wiki organize] 任务: %s", task)
        output = await run_wiki_organize(task, settings)
        return {"message": "Wiki 整理完成", "output": output}
    except Exception as e:  # noqa: BLE001
        logger.error("Wiki organize error: %s", e)
        raise HTTPException(status_code=500, detail="Wiki 整理失败")


@router.post("/admin/wiki/query")
async def query_wiki(body: WikiQueryBody, _user: dict = Depends(get_current_user)):
    if not body.question:
        raise HTTPException(status_code=400, detail="缺少问题")
    try:
        settings = await get_settings()
        output = await run_wiki_query(body.question, settings)
        return {"answer": output}
    except Exception as e:  # noqa: BLE001
        logger.error("Wiki query error: %s", e)
        raise HTTPException(status_code=500, detail="Wiki 查询失败")
