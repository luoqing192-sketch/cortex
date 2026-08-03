"""评分器协议。评分器接收用例与轨迹，返回 Score。"""
from __future__ import annotations

from typing import Protocol

from evals.models import Case, Score, Trajectory


class Grader(Protocol):
    def __call__(self, case: Case, traj: Trajectory, args: dict) -> Score: ...


def ok(name: str, reason: str = "") -> Score:
    return Score(grader=name, passed=True, score=1.0, reason=reason)


def fail(name: str, reason: str) -> Score:
    return Score(grader=name, passed=False, score=0.0, reason=reason)
