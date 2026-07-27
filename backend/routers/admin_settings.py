from fastapi import APIRouter, Depends, Request

from auth import require_admin
from db import execute, fetch_all

router = APIRouter()


@router.get("/admin/settings")
async def get_settings(_admin: dict = Depends(require_admin)):
    rows = await fetch_all("SELECT setting_key, setting_value FROM settings ORDER BY setting_key")
    return {r["setting_key"]: r["setting_value"] for r in rows}


@router.put("/admin/settings")
async def update_settings(request: Request, _admin: dict = Depends(require_admin)):
    body = await request.json()
    for key, value in body.items():
        await execute(
            "INSERT INTO settings (setting_key, setting_value) VALUES (?, ?) "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, "
            "updated_at = datetime('now')",
            (key, value),
        )
    return {"message": "设置已更新"}
