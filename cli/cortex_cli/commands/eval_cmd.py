"""cortex eval —— 运行评测套件、看报告、列历史。

评测逻辑在 backend（复用 LocalEngine），故本命令需 backend 可导入（同 --local）。
"""
from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.table import Table

from cortex_cli.console import get_console

console = get_console()
eval_app = typer.Typer(help="自动评测（Phase 1：确定性）")


def _require_backend():
    try:
        import evals.orchestrator  # noqa: F401
        return
    except ImportError:
        pass
    # 回退：若未安装 backend 包，尝试把同仓库 backend/ 加到 sys.path
    import sys
    from pathlib import Path

    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "backend"
        if (cand / "evals" / "orchestrator.py").exists():
            sys.path.insert(0, str(cand))
            try:
                import evals.orchestrator  # noqa: F401
                return
            except ImportError:
                break
    console.print("[red]无法导入 backend evals 模块[/]")
    console.print("[dim]需安装 backend：pip install -e backend/（或从仓库根运行）[/]")
    raise typer.Exit(1)


@eval_app.command("run")
def run(
    suite: Optional[str] = typer.Argument(None, help="套件名（不指定则跑全部）"),
    baseline: Optional[int] = typer.Option(None, "--baseline", help="与历史 run 对比出回归 diff"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON"),
    fail_under: Optional[float] = typer.Option(None, "--fail-under", help="通过率低于此值则退出码=1"),
):
    """运行评测套件。"""
    _require_backend()
    from evals.orchestrator import run_suite
    from evals.report import diff_against_baseline, report_to_dict, to_json, to_markdown
    from evals.schema import close_eval_conn
    from db import close_conn

    async def go():
        def progress(i, n, case):
            if not json_output:
                console.print(f"[dim]({i}/{n}) {case.id}[/]")
        report = await run_suite(suite, progress=progress)

        diff = None
        if baseline is not None:
            diff = await diff_against_baseline(report, baseline)

        await close_eval_conn()
        await close_conn()
        return report, diff

    try:
        report, diff = asyncio.run(go())
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]评测失败: {e}[/]")
        raise typer.Exit(1)

    if json_output:
        import json as _json
        out = report_to_dict(report)
        if diff:
            out["baseline_diff"] = diff
        console.print(_json.dumps(out, ensure_ascii=False, indent=2))
    else:
        console.print(to_markdown(report))
        if diff and "error" not in diff:
            delta = diff["pass_rate_delta"]
            color = "green" if delta >= 0 else "red"
            console.print(
                f"\n[bold]对比 baseline run {diff['baseline_run_id']}[/]："
                f"通过率 [{color}]{delta:+.1%}[/]"
            )
            if diff["newly_failed"]:
                console.print(f"[red]新失败: {', '.join(diff['newly_failed'])}[/]")
            if diff["newly_passed"]:
                console.print(f"[green]新通过: {', '.join(diff['newly_passed'])}[/]")

    if fail_under is not None and report.pass_rate < fail_under:
        console.print(
            f"\n[red]✗ 通过率 {report.pass_rate:.1%} < 门禁 {fail_under:.1%}[/]"
        )
        raise typer.Exit(1)


@eval_app.command("list")
def list_runs_cmd(limit: int = typer.Option(20, "--limit", "-n")):
    """列出历史评测 run。"""
    _require_backend()
    from evals.schema import close_eval_conn, list_runs

    async def go():
        rows = await list_runs(limit)
        await close_eval_conn()
        return rows

    rows = asyncio.run(go())
    table = Table(show_header=True, header_style="bold")
    for col in ("ID", "套件", "通过", "通过率", "延迟", "模型", "git", "时间"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r["id"]), r["suite"], f"{r['passed']}/{r['total']}",
            f"{(r['pass_rate'] or 0) * 100:.0f}%", f"{r['avg_latency_ms']}ms",
            str(r.get("model") or "-"), str(r.get("git_sha") or "-"),
            str(r.get("started_at") or ""),
        )
    console.print(table)


@eval_app.command("report")
def report_cmd(run_id: int = typer.Argument(..., help="run ID")):
    """打印某次 run 的详细结果。"""
    _require_backend()
    from evals.schema import close_eval_conn, get_run, get_run_results

    async def go():
        run = await get_run(run_id)
        results = await get_run_results(run_id)
        await close_eval_conn()
        return run, results

    run, results = asyncio.run(go())
    if not run:
        console.print(f"[red]run {run_id} 不存在[/]")
        raise typer.Exit(1)

    console.print(
        f"[bold]run {run_id}[/] · 套件 {run['suite']} · "
        f"{run['passed']}/{run['total']} ({(run['pass_rate'] or 0) * 100:.1f}%) · "
        f"模型 {run.get('model')} · git {run.get('git_sha')}"
    )
    table = Table(show_header=True, header_style="bold")
    for col in ("用例", "路由", "结果", "延迟", "错误/失败项"):
        table.add_column(col)
    import json as _json
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        detail = r.get("error") or ""
        if not detail:
            scores = _json.loads(r["scores_json"] or "[]")
            detail = ", ".join(s["grader"] for s in scores if not s["passed"])
        table.add_row(r["case_id"], r.get("route") or "-", mark,
                      f"{r['latency_ms']}ms", detail or "-")
    console.print(table)


@eval_app.command("suites")
def suites_cmd():
    """列出可用套件。"""
    _require_backend()
    from evals.loader import list_suites

    for s in list_suites():
        console.print(f"  {s}")
