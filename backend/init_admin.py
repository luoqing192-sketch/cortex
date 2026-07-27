"""确保默认管理员存在（admin / 123456）。薄封装，逻辑在 db.ensure_admin。"""
from db import ensure_admin


async def ensure_admin_user() -> None:
    await ensure_admin("admin", "123456")
