"""会话管理命令：conv list / new / rm / switch。"""
from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.table import Table

from cortex_cli import config as cfg
from cortex_cli.console import get_console
from cortex_cli.engine.base import AuthError, EngineError
from cortex_cli.engine.factory import make_engine, resolve_mode

console = get_console()
conv_app = typer.Typer(help="会话管理")


def _engine(local: bool, remote: bool):
    return make_engine(resolve_mode(local, remote))


def _run(coro):
    try:
        return asyncio.run(coro)
    except AuthError as e:
        console.print(f"[red]认证失败: {e}（先 `cortex login`）[/]")
        raise typer.Exit(1)
    except EngineError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)


@conv_app.command("list")
def list_conv(
    local: bool = typer.Option(False, "--local"),
    remote: bool = typer.Option(False, "--remote"),
):
    """列出会话。"""
    engine = _engine(local, remote)
    convs = _run(engine.list_conversations())
    current = cfg.get_setting("last_conversation")
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID"); table.add_column("标题"); table.add_column("更新时间", style="dim")
    for c in convs:
        marker = "→ " if str(c["id"]) == str(current) else ""
        table.add_row(f"{marker}{c['id']}", c.get("title", ""), c.get("updated_at", ""))
    console.print(table)


@conv_app.command("new")
def new_conv(
    title: Optional[str] = typer.Argument(None, help="会话标题"),
    local: bool = typer.Option(False, "--local"),
    remote: bool = typer.Option(False, "--remote"),
):
    """新建会话并设为当前。"""
    engine = _engine(local, remote)
    conv = _run(engine.create_conversation(title))
    cfg.set_setting("last_conversation", conv["id"])
    console.print(f"[green]✓ 新会话 {conv['id']}[/]：{conv.get('title')}")


@conv_app.command("rm")
def rm_conv(
    conversation_id: int = typer.Argument(..., help="会话 ID"),
    local: bool = typer.Option(False, "--local"),
    remote: bool = typer.Option(False, "--remote"),
):
    """删除会话。"""
    engine = _engine(local, remote)
    _run(engine.delete_conversation(conversation_id))
    if str(cfg.get_setting("last_conversation")) == str(conversation_id):
        cfg.set_setting("last_conversation", None)
    console.print(f"[green]✓ 已删除会话 {conversation_id}[/]")


@conv_app.command("switch")
def switch_conv(conversation_id: int = typer.Argument(..., help="会话 ID")):
    """切换当前会话（仅记录到本地配置）。"""
    cfg.set_setting("last_conversation", conversation_id)
    console.print(f"[green]✓ 当前会话 → {conversation_id}[/]")
