"""交互式 REPL —— 输入即发流式渲染 + 斜杠命令。"""
from __future__ import annotations

import asyncio

from rich.table import Table

from cortex_cli import config as cfg
from cortex_cli.console import get_console
from cortex_cli.engine.base import AuthError, Engine, EngineError
from cortex_cli.render import render_stream

console = get_console()

HELP = """[bold]斜杠命令[/]
  /new [标题]      新建会话并切换
  /list            列出会话
  /switch <id>     切换会话
  /rm <id>         删除会话
  /image <path>    为下一条消息附加图片
  /images          查看待发图片
  /clear           清空待发图片
  /help            显示帮助
  /exit            退出（或 Ctrl-D）"""


class ReplSession:
    def __init__(self, engine: Engine, conversation_id: int | None, mode_label: str):
        self.engine = engine
        self.conversation_id = conversation_id
        self.mode_label = mode_label
        self.pending_images: list[dict] = []

    async def ensure_conversation(self):
        if self.conversation_id is None:
            conv = await self.engine.create_conversation()
            self.conversation_id = conv["id"]
            cfg.set_setting("last_conversation", self.conversation_id)

    def _prompt_str(self) -> str:
        imgs = f" 🖼×{len(self.pending_images)}" if self.pending_images else ""
        return f"[{self.mode_label} · conv {self.conversation_id}{imgs}] › "

    async def run(self):
        await self.ensure_conversation()
        console.print(f"[dim]Cortex REPL · {self.mode_label} · 会话 {self.conversation_id} · /help 查看命令[/]")
        while True:
            try:
                line = console.input(self._prompt_str())
            except EOFError:
                console.print("\n[dim]再见[/]")
                return
            except KeyboardInterrupt:
                console.print("[dim](Ctrl-D 或 /exit 退出)[/]")
                continue

            line = line.strip()
            if not line:
                continue
            if line.startswith("/"):
                if await self._handle_slash(line):
                    return
                continue

            await self._send(line)

    async def _send(self, message: str):
        attachments = self.pending_images or None
        try:
            events = self.engine.stream_chat(self.conversation_id, message, attachments)
            await render_stream(events, console)
            self.pending_images = []
        except AuthError as e:
            console.print(f"[red]认证失败: {e}[/]")
        except EngineError as e:
            console.print(f"[red]{e}[/]")
        except KeyboardInterrupt:
            console.print("\n[yellow]已中断本次回复[/]")

    async def _handle_slash(self, line: str) -> bool:
        """处理斜杠命令，返回 True 表示退出。"""
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit", "/q"):
            return True
        if cmd == "/help":
            console.print(HELP)
        elif cmd == "/new":
            conv = await self.engine.create_conversation(arg or None)
            self.conversation_id = conv["id"]
            cfg.set_setting("last_conversation", self.conversation_id)
            console.print(f"[green]✓ 新会话 {self.conversation_id}[/]")
        elif cmd == "/list":
            convs = await self.engine.list_conversations()
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID"); table.add_column("标题"); table.add_column("更新时间", style="dim")
            for c in convs[:30]:
                marker = "→ " if c["id"] == self.conversation_id else ""
                table.add_row(f"{marker}{c['id']}", c.get("title", ""), c.get("updated_at", ""))
            console.print(table)
        elif cmd == "/switch":
            if arg.isdigit():
                self.conversation_id = int(arg)
                cfg.set_setting("last_conversation", self.conversation_id)
                console.print(f"[green]✓ 切换到会话 {self.conversation_id}[/]")
            else:
                console.print("[yellow]用法: /switch <id>[/]")
        elif cmd == "/rm":
            if arg.isdigit():
                await self.engine.delete_conversation(int(arg))
                console.print(f"[green]✓ 已删除会话 {arg}[/]")
            else:
                console.print("[yellow]用法: /rm <id>[/]")
        elif cmd == "/image":
            await self._add_image(arg)
        elif cmd == "/images":
            if self.pending_images:
                for im in self.pending_images:
                    console.print(f"  🖼 {im.get('name')}")
            else:
                console.print("[dim](无待发图片)[/]")
        elif cmd == "/clear":
            self.pending_images = []
            console.print("[green]✓ 已清空待发图片[/]")
        else:
            console.print(f"[yellow]未知命令 {cmd}，/help 查看[/]")
        return False

    async def _add_image(self, path: str):
        if not path:
            console.print("[yellow]用法: /image <path>[/]")
            return
        try:
            ref = await self.engine.upload_image(path)
            self.pending_images.append(ref)
            console.print(f"[green]✓ 已附加 🖼 {ref.get('name')}[/]")
        except NotImplementedError:
            console.print("[yellow]当前模式不支持图片[/]")
        except (EngineError, AuthError) as e:
            console.print(f"[red]{e}[/]")
