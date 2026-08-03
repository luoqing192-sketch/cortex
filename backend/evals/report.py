"""报告：聚合 + baseline diff + markdown/JSON 输出。"""
from __future__ import annotations

import json

from evals.models import RunReport
from evals.schema import get_run, get_run_results


def report_to_dict(report: RunReport) -> dict:
    return {
        "run_id": report.run_id,
        "suite": report.suite,
        "total": report.total,
        "passed": report.passed,
        "pass_rate": round(report.pass_rate, 4),
        "avg_latency_ms": report.avg_latency_ms,
        "errors": report.errors,
        "cases": [
            {
                "case_id": r.case_id,
                "route": r.route,
                "passed": r.passed,
                "latency_ms": r.latency_ms,
                "error": r.error,
                "scores": [
                    {"grader": s.grader, "passed": s.passed, "reason": s.reason}
                    for s in r.scores
                ],
            }
            for r in report.results
        ],
    }


def to_json(report: RunReport) -> str:
    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)


def to_markdown(report: RunReport) -> str:
    lines = [
        f"# 评测报告 · run {report.run_id} · 套件 {report.suite}",
        "",
        f"- 通过率：**{report.passed}/{report.total}** "
        f"({report.pass_rate * 100:.1f}%)",
        f"- 平均延迟：{report.avg_latency_ms} ms",
        f"- 错误数：{report.errors}",
        "",
        "| 用例 | 路由 | 结果 | 延迟 | 失败评分器 |",
        "|------|------|------|------|-----------|",
    ]
    for r in report.results:
        mark = "✅" if r.passed else "❌"
        failed = ", ".join(f"{s.grader}({s.reason})" for s in r.scores if not s.passed)
        lines.append(
            f"| {r.case_id} | {r.route} | {mark} | {r.latency_ms}ms | {failed or '-'} |"
        )
    return "\n".join(lines)


async def diff_against_baseline(report: RunReport, baseline_run_id: int) -> dict:
    """与历史 run 对比，列出新失败/新通过。"""
    base_run = await get_run(baseline_run_id)
    if not base_run:
        return {"error": f"baseline run {baseline_run_id} 不存在"}

    base_results = await get_run_results(baseline_run_id)
    base_pass = {r["case_id"]: bool(r["passed"]) for r in base_results}

    newly_failed, newly_passed = [], []
    for r in report.results:
        was = base_pass.get(r.case_id)
        if was is None:
            continue
        if was and not r.passed:
            newly_failed.append(r.case_id)
        elif not was and r.passed:
            newly_passed.append(r.case_id)

    return {
        "baseline_run_id": baseline_run_id,
        "baseline_pass_rate": base_run["pass_rate"],
        "current_pass_rate": round(report.pass_rate, 4),
        "pass_rate_delta": round(report.pass_rate - base_run["pass_rate"], 4),
        "newly_failed": newly_failed,   # ← 回归
        "newly_passed": newly_passed,
    }
