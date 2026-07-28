"""配置命令：config get / set / list。"""
from __future__ import annotations

import typer
from rich.table import Table

from cortex_cli import config as cfg
from cortex_cli.console import get_console

console = get_console()
config_app = typer.Typer(help="本地配置（~/.cortex/config.toml）")


@config_app.command("list")
def list_config():
    """列出所有配置项。"""
    data = cfg.load_config()
    table = Table(show_header=True, header_style="bold")
    table.add_column("键"); table.add_column("值")
    for k, v in data.items():
        table.add_row(k, str(v))
    console.print(table)


@config_app.command("get")
def get_config(key: str = typer.Argument(..., help="配置键")):
    """读取一个配置项。"""
    console.print(str(cfg.get_setting(key)))


@config_app.command("set")
def set_config(
    key: str = typer.Argument(..., help="配置键，如 api_url / mode / last_conversation"),
    value: str = typer.Argument(..., help="值"),
):
    """设置一个配置项。"""
    cfg.set_setting(key, value)
    console.print(f"[green]✓ {key} = {cfg.get_setting(key)}[/]")
