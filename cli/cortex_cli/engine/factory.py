"""按 mode 构建 Engine。"""
from __future__ import annotations

from cortex_cli import config as cfg
from cortex_cli.engine.base import Engine


def make_engine(mode: str) -> Engine:
    api_url = cfg.get_setting("api_url")
    if mode == "local":
        from cortex_cli.engine.local import LocalEngine  # 延迟导入，避免无 backend 时报错

        return LocalEngine()
    token = cfg.load_token(api_url)
    from cortex_cli.engine.remote import RemoteEngine

    return RemoteEngine(api_url, token)


def resolve_mode(local: bool, remote: bool) -> str:
    mode = cfg.get_setting("mode") or "remote"
    if local:
        return "local"
    if remote:
        return "remote"
    return mode
