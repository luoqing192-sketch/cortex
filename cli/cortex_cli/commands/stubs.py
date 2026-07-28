"""预留命令壳 —— 对应后续平台化能力（skill / mcp / schedule / admin）。

现在仅占位，避免后续接入时改动命令树结构。实现时替换各命令体即可。
"""
from __future__ import annotations

import typer

from cortex_cli.console import get_console

console = get_console()

_NOT_YET = "[yellow]该命令尚未实现（平台化能力路线预留）。[/]"


def _stub_app(help_text: str) -> typer.Typer:
    a = typer.Typer(help=help_text)

    @a.callback(invoke_without_command=True)
    def _default(ctx: typer.Context):
        if ctx.invoked_subcommand is None:
            console.print(_NOT_YET)

    return a


# skill：开发/测试/发布/部署技能
skill_app = _stub_app("技能管理（预留）：list / test / install / enable")


@skill_app.command("list")
def skill_list():
    console.print(_NOT_YET)


# mcp：MCP server 管理
mcp_app = _stub_app("MCP 管理（预留）：list / add / rm / enable")


@mcp_app.command("list")
def mcp_list():
    console.print(_NOT_YET)


# schedule：定时任务
schedule_app = _stub_app("定时任务（预留）：list / add / rm")


@schedule_app.command("list")
def schedule_list():
    console.print(_NOT_YET)
