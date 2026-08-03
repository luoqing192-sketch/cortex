"""从 datasets/*.yaml 加载评测用例并校验。"""
from __future__ import annotations

from pathlib import Path

import yaml

from evals.models import Case, GraderSpec

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

VALID_ROUTES = {"intent", "knowledge_qa", "generate_page", "web_research", "casual_chat"}


class DatasetError(Exception):
    pass


def _parse_graders(raw: list, case_id: str) -> list[GraderSpec]:
    from evals.graders import GRADER_REGISTRY  # 延迟导入避免循环

    specs = []
    for g in raw or []:
        if not isinstance(g, dict) or "name" not in g:
            raise DatasetError(f"用例 {case_id}: grader 必须是 {{name, args?}}，得到 {g!r}")
        name = g["name"]
        if name not in GRADER_REGISTRY:
            raise DatasetError(
                f"用例 {case_id}: 未知 grader '{name}'，可用: {sorted(GRADER_REGISTRY)}"
            )
        specs.append(GraderSpec(name=name, args=g.get("args", {}) or {}))
    if not specs:
        raise DatasetError(f"用例 {case_id}: 至少需要一个 grader")
    return specs


def load_file(path: Path) -> list[Case]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DatasetError(f"{path.name}: 顶层必须是 mapping")

    suite = data.get("suite") or path.stem
    route = data.get("route") or suite
    if route not in VALID_ROUTES:
        raise DatasetError(f"{path.name}: route '{route}' 非法，应为 {sorted(VALID_ROUTES)}")

    cases: list[Case] = []
    seen_ids = set()
    for raw in data.get("cases", []):
        cid = raw.get("id")
        if not cid:
            raise DatasetError(f"{path.name}: 存在缺少 id 的用例")
        if cid in seen_ids:
            raise DatasetError(f"{path.name}: 重复用例 id '{cid}'")
        seen_ids.add(cid)

        inp = raw.get("input") or {}
        if not inp.get("message"):
            raise DatasetError(f"用例 {cid}: input.message 不能为空")

        cases.append(Case(
            id=cid,
            suite=suite,
            route=route,
            input=inp,
            graders=_parse_graders((raw.get("expected") or {}).get("graders"), cid),
            tags=raw.get("tags", []) or [],
        ))
    return cases


def load_suite(suite: str | None = None) -> list[Case]:
    """加载指定 suite（= 文件名，不含 .yaml）；None 加载全部。"""
    if not DATASETS_DIR.exists():
        raise DatasetError(f"数据集目录不存在: {DATASETS_DIR}")

    if suite:
        path = DATASETS_DIR / f"{suite}.yaml"
        if not path.exists():
            raise DatasetError(f"套件不存在: {path}")
        return load_file(path)

    cases: list[Case] = []
    for path in sorted(DATASETS_DIR.glob("*.yaml")):
        cases.extend(load_file(path))
    return cases


def list_suites() -> list[str]:
    if not DATASETS_DIR.exists():
        return []
    return sorted(p.stem for p in DATASETS_DIR.glob("*.yaml"))
