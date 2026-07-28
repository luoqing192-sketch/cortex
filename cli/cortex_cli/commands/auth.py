"""认证命令：login / logout / whoami。"""
from __future__ import annotations

import asyncio
import getpass
from typing import Optional

import typer

from cortex_cli import config as cfg
from cortex_cli.console import get_console
from cortex_cli.engine.base import AuthError, EngineError
from cortex_cli.engine.remote import RemoteEngine

console = get_console()


def login_cmd(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="用户名"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="密码（省略则交互输入）"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="后端地址（覆盖配置）"),
):
    """登录后端并保存 token。"""
    url = api_url or cfg.get_setting("api_url")
    if api_url:
        cfg.set_setting("api_url", api_url)

    if not username:
        username = typer.prompt("用户名")
    if not password:
        password = getpass.getpass("密码: ")

    engine = RemoteEngine(url, None)
    try:
        result = asyncio.run(engine.login(username, password))
    except AuthError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
    except EngineError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)

    cfg.save_token(url, result["token"])
    user = result.get("user", {})
    console.print(f"[green]✓ 登录成功[/]：{user.get('username')} ({user.get('role')}) @ {url}")


def logout_cmd(
    api_url: Optional[str] = typer.Option(None, "--api-url", help="后端地址"),
):
    """清除本地 token。"""
    url = api_url or cfg.get_setting("api_url")
    cfg.delete_token(url)
    console.print(f"[green]✓ 已登出[/] @ {url}")


def whoami_cmd(
    api_url: Optional[str] = typer.Option(None, "--api-url", help="后端地址"),
):
    """显示当前登录用户。"""
    url = api_url or cfg.get_setting("api_url")
    token = cfg.load_token(url)
    if not token:
        console.print("[yellow]未登录，请先 `cortex login`[/]")
        raise typer.Exit(1)
    engine = RemoteEngine(url, token)
    try:
        user = asyncio.run(engine.whoami())
    except EngineError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
    if not user:
        console.print("[yellow]token 已失效，请重新 `cortex login`[/]")
        raise typer.Exit(1)
    console.print(f"[cyan]{user.get('username')}[/] (id={user.get('id')}, role={user.get('role')})")
