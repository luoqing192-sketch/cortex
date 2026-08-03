"""评测运行期数据类。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraderSpec:
    """一个用例要跑的评分器 + 参数。"""
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class Case:
    id: str
    suite: str
    route: str
    input: dict                       # {message, seed_history?, attachments?}
    graders: list[GraderSpec]
    tags: list[str] = field(default_factory=list)


@dataclass
class Trajectory:
    """一次对话跑完后从事件流采集到的信号。"""
    intent: str | None = None
    tool_calls: list[dict] = field(default_factory=list)   # [{tool,status}]
    sources: list[dict] = field(default_factory=list)
    preview_url: str | None = None
    answer: str = ""
    artifacts_dir: str = ""
    latency_ms: int = 0
    error: str | None = None


@dataclass
class Score:
    grader: str
    passed: bool
    score: float           # 0.0 - 1.0
    reason: str = ""


@dataclass
class CaseResult:
    case_id: str
    route: str
    trajectory: Trajectory
    scores: list[Score]
    latency_ms: int
    error: str | None = None

    @property
    def passed(self) -> bool:
        return bool(self.scores) and all(s.passed for s in self.scores)


@dataclass
class RunReport:
    run_id: int
    suite: str
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def avg_latency_ms(self) -> int:
        if not self.results:
            return 0
        return round(sum(r.latency_ms for r in self.results) / len(self.results))

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.error)
