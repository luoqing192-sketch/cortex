"""评测体系离线单测：loader / graders / runner（假引擎，无 LLM 依赖）。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.loader import load_suite, list_suites, DatasetError  # noqa: E402
from evals.graders import GRADER_REGISTRY  # noqa: E402
from evals.models import Case, GraderSpec, Trajectory  # noqa: E402


# ---------------- loader ----------------
def test_load_seed_suites():
    for suite in ("intent", "casual_chat", "generate_page"):
        cases = load_suite(suite)
        assert cases, f"{suite} 无用例"
        for c in cases:
            assert c.id and c.input.get("message") and c.graders


def test_list_suites():
    s = set(list_suites())
    assert {"intent", "casual_chat", "generate_page"} <= s


# ---------------- graders ----------------
def _case():
    return Case(id="t", suite="s", route="intent", input={"message": "x"}, graders=[])


def test_intent_match():
    g = GRADER_REGISTRY["intent_match"]
    assert g(_case(), Trajectory(intent="web_research"), {"expected": "web_research"}).passed
    assert not g(_case(), Trajectory(intent="casual_chat"), {"expected": "web_research"}).passed


def test_must_contain_and_not():
    mc = GRADER_REGISTRY["must_contain"]
    mn = GRADER_REGISTRY["must_not_contain"]
    t = Trajectory(answer="不支持闲聊能力，请用知识库问答或页面生成")
    assert mc(_case(), t, {"value": "不支持闲聊"}).passed
    assert mc(_case(), t, {"values": ["知识库", "页面生成"]}).passed
    assert not mc(_case(), t, {"value": "缺失词"}).passed
    assert mn(_case(), t, {"value": "Traceback"}).passed
    assert not mn(_case(), t, {"value": "闲聊"}).passed


def test_tool_called_and_preview():
    tc = GRADER_REGISTRY["tool_called"]
    pe = GRADER_REGISTRY["preview_emitted"]
    t = Trajectory(tool_calls=[{"tool": "generate_code", "status": "running"}],
                   preview_url="/preview/1/index.html")
    assert tc(_case(), t, {"tool": "generate_code"}).passed
    assert not tc(_case(), t, {"tool": "web_search"}).passed
    assert pe(_case(), t, {}).passed
    assert not pe(_case(), Trajectory(), {}).passed


def test_file_and_html(tmp_path):
    fe = GRADER_REGISTRY["file_exists"]
    hp = GRADER_REGISTRY["html_parses"]
    (tmp_path / "index.html").write_text("<html><body><h1>hi</h1></body></html>", encoding="utf-8")
    t = Trajectory(artifacts_dir=str(tmp_path))
    assert fe(_case(), t, {"path": "index.html"}).passed
    assert not fe(_case(), t, {"path": "missing.html"}).passed
    assert hp(_case(), t, {"path": "index.html"}).passed


def test_sources_and_no_error():
    sn = GRADER_REGISTRY["sources_nonempty"]
    ne = GRADER_REGISTRY["no_error"]
    assert sn(_case(), Trajectory(sources=[{"url": "x"}]), {}).passed
    assert not sn(_case(), Trajectory(sources=[]), {}).passed
    assert ne(_case(), Trajectory(error=None), {}).passed
    assert not ne(_case(), Trajectory(error="boom"), {}).passed


# ---------------- runner（假引擎，验证事件流→Trajectory 采集）----------------
class _FakeEngine:
    """产出固定事件序列的假引擎，验证 runner 采集逻辑，不碰 LLM/DB。"""
    def __init__(self, events):
        self._events = events

    async def create_conversation(self, title=None):
        return {"id": 999}

    async def stream_chat(self, conv_id, message, attachments=None):
        from cortex_cli.events import ChatEvent
        for e in self._events:
            yield ChatEvent(type=e["type"], content=e.get("content", ""), data=e.get("data", {}))

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_runner_collects_trajectory(monkeypatch):
    # runner 会调用 db.execute 写 seed_history / LocalEngine 建会话；这里不传 seed 所以不写库。
    from evals import runner
    events = [
        {"type": "intent", "data": {"intent": "generate_page"}},
        {"type": "tool_progress", "data": {"tool": "generate_code", "status": "running"}},
        {"type": "tool_progress", "data": {"tool": "generate_code", "status": "completed"}},
        {"type": "content", "content": "我已经生成了页面"},
        {"type": "preview", "data": {"url": "/preview/999/index.html"}},
        {"type": "done"},
    ]
    case = Case(id="r1", suite="s", route="generate_page",
                input={"message": "做个页面"}, graders=[])
    traj = await runner.run_case(_FakeEngine(events), case)
    assert traj.intent == "generate_page"
    assert traj.answer == "我已经生成了页面"
    assert traj.preview_url.endswith("index.html")
    assert {"tool": "generate_code", "status": "running"} in traj.tool_calls
    assert traj.error is None
