"""Cortex CLI 主入口 —— Typer app。"""
from __future__ import annotations

import sys
from typing import Optional

import typer

from cortex_cli import __version__
from cortex_cli import config as cfg
from cortex_cli.commands import auth, chat
from cortex_cli.commands.conv import conv_app
from cortex_cli.commands.config_cmd import config_app
from cortex_cli.commands.stubs import skill_app, mcp_app, schedule_app

# UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore
    except Exception:
        pass

app = typer.Typer(
    name="cortex",
    help="Cortex 终端客户端 —— 交互式对话 / 代码生成 / 网络研究",
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"cortex-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本号"
    ),
):
    pass


# 挂子命令
app.command("chat")(chat.chat_cmd)
app.command("login")(auth.login_cmd)
app.command("logout")(auth.logout_cmd)
app.command("whoami")(auth.whoami_cmd)
app.add_typer(conv_app, name="conv")
app.add_typer(config_app, name="config")
app.add_typer(skill_app, name="skill")
app.add_typer(mcp_app, name="mcp")
app.add_typer(schedule_app, name="schedule")


if __name__ == "__main__":
    app()
