"""cortex chat 命令 —— 一次性对话 + 无参进 REPL。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import typer

from cortex_cli import config as cfg
from cortex_cli.console import get_console
from cortex_cli.engine.base import AuthError, EngineError
from cortex_cli.engine.factory import make_engine, resolve_mode
from cortex_cli.render import render_stream

console = get_console()


def chat_cmd(
    message: Optional[str] = typer.Argument(None, help="消息内容；省略进 REPL；'-' 从 stdin 读"),
    conversation: Optional[int] = typer.Option(
        None, "--conversation", "-c", help="会话 ID（默认用 last 或新建）"
    ),
    image: Optional[List[str]] = typer.Option(
        None, "--image", help="携带图片（可多次）"
    ),
    local: bool = typer.Option(False, "--local", help="离线模式（进程内直跑）"),
    remote: bool = typer.Option(False, "--remote", help="强制远程模式"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="只输出最终回答"),
    json_output: bool = typer.Option(False, "--json", help="NDJSON 事件流"),
):
    """发送消息并流式查看回复；无消息参数则进入交互式 REPL。"""
    mode = resolve_mode(local, remote)
    try:
        engine = make_engine(mode)
    except ImportError as e:
        console.print(f"[red]无法初始化 {mode} 引擎: {e}[/]")
        console.print("[dim]local 模式需安装 backend：pip install -e backend/[/]")
        raise typer.Exit(1)

    mode_label = "local" if mode == "local" else f"remote@{cfg.get_setting('api_url')}"

    # 无参 → REPL
    if message is None and not sys.stdin.isatty():
        message = sys.stdin.read()  # 有管道输入时读 stdin
    if message == "-":
        message = sys.stdin.read()

    if message is None:
        _run_repl(engine, conversation, mode_label)
        return

    try:
        asyncio.run(
            _one_shot(engine, message, conversation, image or [], quiet, json_output)
        )
    except AuthError as e:
        console.print(f"[red]认证失败: {e}[/]")
        raise typer.Exit(1)
    except EngineError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]已中断[/]")
        raise typer.Exit(130)


def _run_repl(engine, conversation, mode_label):
    from cortex_cli.repl import ReplSession

    session = ReplSession(engine, conversation, mode_label)
    try:
        asyncio.run(session.run())
    except KeyboardInterrupt:
        console.print("\n[dim]再见[/]")
    finally:
        asyncio.run(engine.close())


async def _one_shot(engine, message, conversation, images, quiet, json_output):
    # 会话解析
    if conversation is None:
        last = cfg.get_setting("last_conversation")
        if last:
            conversation = int(last)
        else:
            conv = await engine.create_conversation()
            conversation = conv["id"]
            cfg.set_setting("last_conversation", conversation)

    # 图片上传 → 引用
    attachments = []
    for path in images:
        if not Path(path).exists():
            console.print(f"[red]图片不存在: {path}[/]")
            raise typer.Exit(1)
        ref = await engine.upload_image(path)
        attachments.append(ref)
        if not json_output and not quiet:
            console.print(f"[dim]🖼 {ref.get('name')}[/]")

    events = engine.stream_chat(conversation, message, attachments or None)
    await render_stream(events, console, quiet=quiet, json_output=json_output)
    await engine.close()
