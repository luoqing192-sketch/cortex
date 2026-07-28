"""终端渲染 —— 消费 ChatEvent 流，用 Rich 做流式/工具进度/来源/预览展示。

三种输出模式：
- 默认：Rich Live + Markdown 流式渲染 + 工具进度/来源/预览
- quiet：只输出最终回答纯文本（可管道）
- json：每事件一行 NDJSON
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from cortex_cli.events import ChatEvent

_TOOL_LABELS = {
    "web_search": "联网搜索",
    "fetch_webpage": "读取网页",
    "generate_code": "生成代码",
    "read_file": "读取文件",
    "search_codebase": "搜索代码",
    "get_project_structure": "查看结构",
    "get_symbol_definition": "查找符号",
    "run_command": "执行命令",
}
_STATUS_ICON = {"running": "⚙", "completed": "✓", "error": "✗"}


async def render_stream(
    events: AsyncIterator[ChatEvent],
    console: Console,
    *,
    quiet: bool = False,
    json_output: bool = False,
) -> str:
    """渲染事件流，返回最终回答文本。"""
    if json_output:
        return await _render_json(events, console)
    if quiet:
        return await _render_quiet(events, console)
    return await _render_rich(events, console)


async def _render_json(events, console) -> str:
    buf = []
    async for e in events:
        if e.type == "content":
            buf.append(e.content)
        console.print(json.dumps(
            {"type": e.type, "content": e.content, "data": e.data}, ensure_ascii=False
        ))
        if e.type == "done":
            break
    return "".join(buf)


async def _render_quiet(events, console) -> str:
    buf = []
    async for e in events:
        if e.type == "content":
            buf.append(e.content)
        elif e.type == "error":
            console.print(f"[red]{e.data.get('message', 'error')}[/]", highlight=False)
        elif e.type == "done":
            break
    text = "".join(buf)
    if text:
        console.print(text, end="", highlight=False)
    return text


async def _render_rich(events, console) -> str:
    buf: list[str] = []
    tools: list[str] = []  # 已完成/进行中的工具行
    sources: list[dict] = []
    preview_url: str | None = None
    notices: list[str] = []

    def build():
        parts = []
        for n in notices:
            parts.append(Text(f"ⓘ {n}", style="yellow"))
        for t in tools:
            parts.append(Text(t, style="dim cyan"))
        if buf:
            parts.append(Markdown("".join(buf)))
        return Group(*parts) if parts else Text("…", style="dim")

    with Live(build(), console=console, refresh_per_second=12, vertical_overflow="visible") as live:
        async for e in events:
            if e.type == "content":
                buf.append(e.content)
            elif e.type == "tool_progress":
                tool = e.data.get("tool", "")
                status = e.data.get("status", "")
                label = _TOOL_LABELS.get(tool, tool)
                icon = _STATUS_ICON.get(status, "•")
                line = f"{icon} {label}"
                # 更新同名工具的最后一行，或追加
                replaced = False
                for i in range(len(tools) - 1, -1, -1):
                    if label in tools[i]:
                        tools[i] = line
                        replaced = True
                        break
                if not replaced:
                    tools.append(line)
            elif e.type == "notice":
                notices.append(e.data.get("message", ""))
            elif e.type == "queue":
                notices.append(f"排队中 pending={e.data.get('pending')} active={e.data.get('active')}")
            elif e.type == "sources":
                sources = e.data.get("sources", [])
            elif e.type == "preview":
                preview_url = e.data.get("url")
            elif e.type == "intent":
                pass  # 信息性
            elif e.type == "error":
                buf.append(f"\n\n**错误**: {e.data.get('message', 'unknown')}")
            elif e.type == "done":
                break
            live.update(build())

    # 尾部附加信息
    if sources:
        lines = [f"[cyan]{i+1}.[/] {s.get('title') or s.get('url')}\n   [dim]{s.get('url')}[/]"
                 for i, s in enumerate(sources)]
        console.print(Panel("\n".join(lines), title="参考来源", border_style="cyan", expand=False))
    if preview_url:
        console.print(f"[green]🔗 预览：[/]{preview_url}")

    return "".join(buf)
