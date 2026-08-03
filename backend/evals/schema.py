"""评测结果表建表 + 写入辅助。默认独立库 eval.db（不污染业务库）。"""
from __future__ import annotations

import json

import aiosqlite

from config import BASE_DIR
from evals.models import CaseResult, RunReport
from logger import logger

EVAL_DB_PATH = str(BASE_DIR / "eval.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  suite TEXT NOT NULL,
  model TEXT,
  prompt_version TEXT,
  git_sha TEXT,
  config_json TEXT,
  started_at TEXT DEFAULT (datetime('now')),
  finished_at TEXT,
  total INTEGER DEFAULT 0,
  passed INTEGER DEFAULT 0,
  pass_rate REAL DEFAULT 0,
  avg_latency_ms INTEGER DEFAULT 0,
  errors INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS eval_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  case_id TEXT NOT NULL,
  route TEXT,
  trajectory_json TEXT,
  scores_json TEXT,
  passed INTEGER,
  latency_ms INTEGER,
  error TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (run_id) REFERENCES eval_runs(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_eval_results_run ON eval_results(run_id);
"""

_conn: aiosqlite.Connection | None = None


async def get_eval_conn() -> aiosqlite.Connection:
    global _conn
    if _conn is None:
        _conn = await aiosqlite.connect(EVAL_DB_PATH)
        _conn.row_factory = aiosqlite.Row
        await _conn.executescript(_SCHEMA)
        await _conn.commit()
    return _conn


async def close_eval_conn() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


def _traj_dict(t) -> dict:
    return {
        "intent": t.intent, "tool_calls": t.tool_calls, "sources": t.sources,
        "preview_url": t.preview_url, "answer": t.answer,
        "artifacts_dir": t.artifacts_dir, "latency_ms": t.latency_ms, "error": t.error,
    }


async def create_run(suite: str, meta: dict) -> int:
    conn = await get_eval_conn()
    cur = await conn.execute(
        "INSERT INTO eval_runs (suite, model, prompt_version, git_sha, config_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (suite, meta.get("model"), meta.get("prompt_version"), meta.get("git_sha"),
         json.dumps(meta, ensure_ascii=False)),
    )
    await conn.commit()
    return cur.lastrowid


async def save_result(run_id: int, r: CaseResult) -> None:
    conn = await get_eval_conn()
    scores = [{"grader": s.grader, "passed": s.passed, "score": s.score, "reason": s.reason}
              for s in r.scores]
    await conn.execute(
        "INSERT INTO eval_results (run_id, case_id, route, trajectory_json, scores_json, "
        "passed, latency_ms, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, r.case_id, r.route, json.dumps(_traj_dict(r.trajectory), ensure_ascii=False),
         json.dumps(scores, ensure_ascii=False), 1 if r.passed else 0, r.latency_ms, r.error),
    )
    await conn.commit()


async def finalize_run(report: RunReport) -> None:
    conn = await get_eval_conn()
    await conn.execute(
        "UPDATE eval_runs SET finished_at=datetime('now'), total=?, passed=?, pass_rate=?, "
        "avg_latency_ms=?, errors=? WHERE id=?",
        (report.total, report.passed, round(report.pass_rate, 4),
         report.avg_latency_ms, report.errors, report.run_id),
    )
    await conn.commit()
    logger.info("[eval] run %s: %d/%d 通过 (%.1f%%)",
                report.run_id, report.passed, report.total, report.pass_rate * 100)


async def list_runs(limit: int = 20) -> list[dict]:
    conn = await get_eval_conn()
    async with conn.execute(
        "SELECT * FROM eval_runs ORDER BY id DESC LIMIT ?", (limit,)
    ) as cur:
        return [dict(r) for r in await cur.fetchall()]


async def get_run(run_id: int) -> dict | None:
    conn = await get_eval_conn()
    async with conn.execute("SELECT * FROM eval_runs WHERE id=?", (run_id,)) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_run_results(run_id: int) -> list[dict]:
    conn = await get_eval_conn()
    async with conn.execute(
        "SELECT * FROM eval_results WHERE run_id=? ORDER BY id", (run_id,)
    ) as cur:
        return [dict(r) for r in await cur.fetchall()]
