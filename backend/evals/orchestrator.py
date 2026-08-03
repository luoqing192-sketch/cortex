"""编排：load → run_case → grade → 存库 → RunReport。

Phase 1 顺序执行；Phase 4 再上 LangGraph 扇出并发（run_case 只依赖 Engine，无需重构）。
"""
from __future__ import annotations

import subprocess

from evals.graders import GRADER_REGISTRY
from evals.loader import load_suite
from evals.models import Case, CaseResult, RunReport, Score, Trajectory
from evals.runner import _get_engine, run_case
from evals.schema import create_run, finalize_run, save_result
from llm import get_active_prompt, get_settings
from logger import logger


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:  # noqa: BLE001
        return None


def grade_case(case: Case, traj: Trajectory) -> list[Score]:
    scores: list[Score] = []
    for spec in case.graders:
        grader = GRADER_REGISTRY.get(spec.name)
        if grader is None:
            scores.append(Score(spec.name, False, 0.0, "未知评分器"))
            continue
        try:
            scores.append(grader(case, traj, spec.args))
        except Exception as e:  # noqa: BLE001
            scores.append(Score(spec.name, False, 0.0, f"评分器异常: {e}"))
    return scores


async def run_suite(suite: str | None = None, *, progress=None) -> RunReport:
    cases = load_suite(suite)
    if not cases:
        raise ValueError("没有可跑的用例")

    settings = await get_settings()
    active = await get_active_prompt()
    meta = {
        "model": settings.get("llm_model"),
        "prompt_version": (active or {}).get("name"),
        "git_sha": _git_sha(),
        "suite": suite or "all",
        "case_count": len(cases),
    }
    run_id = await create_run(suite or "all", meta)

    engine = _get_engine()
    results: list[CaseResult] = []
    try:
        for i, case in enumerate(cases, 1):
            if progress:
                progress(i, len(cases), case)
            traj = await run_case(engine, case)
            scores = grade_case(case, traj)
            result = CaseResult(
                case_id=case.id, route=case.route, trajectory=traj,
                scores=scores, latency_ms=traj.latency_ms, error=traj.error,
            )
            results.append(result)
            await save_result(run_id, result)
    finally:
        await engine.close()

    report = RunReport(run_id=run_id, suite=suite or "all", results=results)
    await finalize_run(report)
    logger.info("[eval] 完成套件 %s: %d/%d", suite or "all", report.passed, report.total)
    return report
