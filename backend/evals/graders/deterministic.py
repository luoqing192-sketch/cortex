"""确定性评分器 —— 零成本、零抖动，基于事件轨迹与产物文件断言。"""
from __future__ import annotations

import re
from pathlib import Path

from evals.graders.base import fail, ok
from evals.models import Case, Score, Trajectory


def intent_match(case: Case, traj: Trajectory, args: dict) -> Score:
    expected = args.get("expected")
    if traj.intent == expected:
        return ok("intent_match", f"intent={traj.intent}")
    return fail("intent_match", f"期望 {expected}，实际 {traj.intent}")


def must_contain(case: Case, traj: Trajectory, args: dict) -> Score:
    text = traj.answer or ""
    use_regex = args.get("regex", False)
    for needle in args.get("values", []) or ([args["value"]] if "value" in args else []):
        found = re.search(needle, text) if use_regex else (needle in text)
        if not found:
            return fail("must_contain", f"答案未包含 {needle!r}")
    return ok("must_contain")


def must_not_contain(case: Case, traj: Trajectory, args: dict) -> Score:
    text = traj.answer or ""
    use_regex = args.get("regex", False)
    for needle in args.get("values", []) or ([args["value"]] if "value" in args else []):
        found = re.search(needle, text) if use_regex else (needle in text)
        if found:
            return fail("must_not_contain", f"答案不应包含 {needle!r}")
    return ok("must_not_contain")


def tool_called(case: Case, traj: Trajectory, args: dict) -> Score:
    tool = args.get("tool")
    called = {tc.get("tool") for tc in traj.tool_calls}
    if tool in called:
        return ok("tool_called", f"调用了 {tool}")
    return fail("tool_called", f"未调用 {tool}，实际调用 {sorted(c for c in called if c)}")


def preview_emitted(case: Case, traj: Trajectory, args: dict) -> Score:
    if traj.preview_url:
        return ok("preview_emitted", traj.preview_url)
    return fail("preview_emitted", "未发出 preview 事件")


def sources_nonempty(case: Case, traj: Trajectory, args: dict) -> Score:
    n = len(traj.sources or [])
    min_n = args.get("min", 1)
    if n >= min_n:
        return ok("sources_nonempty", f"{n} 个来源")
    return fail("sources_nonempty", f"来源数 {n} < {min_n}")


def file_exists(case: Case, traj: Trajectory, args: dict) -> Score:
    rel = args.get("path", "")
    p = Path(traj.artifacts_dir) / rel
    if p.exists() and p.is_file():
        return ok("file_exists", str(rel))
    return fail("file_exists", f"文件不存在: {rel}")


def html_parses(case: Case, traj: Trajectory, args: dict) -> Score:
    rel = args.get("path", "index.html")
    p = Path(traj.artifacts_dir) / rel
    if not p.exists():
        return fail("html_parses", f"文件不存在: {rel}")
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="ignore"), "lxml")
        if soup.find(True) is None:
            return fail("html_parses", "HTML 解析为空")
        return ok("html_parses", f"{rel} 可解析")
    except Exception as e:  # noqa: BLE001
        return fail("html_parses", f"解析失败: {e}")


def no_error(case: Case, traj: Trajectory, args: dict) -> Score:
    if traj.error:
        return fail("no_error", f"存在错误: {traj.error[:80]}")
    return ok("no_error")
