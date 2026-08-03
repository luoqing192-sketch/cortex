"""评分器注册表 —— 可插拔（同构 skill 机制）。Phase 2 在此追加 LLM 裁判等。"""
from __future__ import annotations

from evals.graders import deterministic as _d

GRADER_REGISTRY = {
    "intent_match": _d.intent_match,
    "must_contain": _d.must_contain,
    "must_not_contain": _d.must_not_contain,
    "tool_called": _d.tool_called,
    "preview_emitted": _d.preview_emitted,
    "sources_nonempty": _d.sources_nonempty,
    "file_exists": _d.file_exists,
    "html_parses": _d.html_parses,
    "no_error": _d.no_error,
}


def get_grader(name: str):
    return GRADER_REGISTRY.get(name)
