"""统一 Console 工厂 —— 规避 Windows GBK/legacy 终端的编码崩溃。"""
from __future__ import annotations

import io
import sys

from rich.console import Console


def _utf8_stdout():
    # 尽量让底层流走 UTF-8；重定向/管道时 reconfigure 可能失败则包一层
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        return sys.stdout
    except Exception:
        try:
            return io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            return sys.stdout


def get_console() -> Console:
    # legacy_windows=False 强制走标准 ANSI 渲染，避开 _win32_console 的 GBK 编码路径
    return Console(file=_utf8_stdout(), legacy_windows=False, force_terminal=None)
