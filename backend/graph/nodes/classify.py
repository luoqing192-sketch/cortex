"""意图分类节点（4 路）。"""
import json
import re

from graph.prompts import INTENT_CLASSIFICATION_PROMPT
from graph.state import GraphState
from llm import build_chat
from logger import logger

VALID_INTENTS = {"knowledge_qa", "generate_page", "web_research", "casual_chat"}
_JSON_RE = re.compile(r"\{[^{}]*\"intent\"[^{}]*\}", re.S)


async def classify_node(state: GraphState) -> dict:
    emit = state["emit"]
    settings = state["settings"]
    message = state["user_message"]
    history = state.get("history", [])

    # 取最近 6 条（约 3 轮）上下文；history 末尾即本次用户消息
    recent = history[-6:] if history else [{"role": "user", "content": message}]
    lc_messages = [{"role": "system", "content": INTENT_CLASSIFICATION_PROMPT}, *recent]

    intent = "knowledge_qa"  # 默认 fallback
    try:
        chat = build_chat(settings, streaming=False, temperature=0.1, max_tokens=50)
        resp = await chat.ainvoke(lc_messages)
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        m = _JSON_RE.search(content)
        parsed = json.loads(m.group(0) if m else content)
        if parsed.get("intent") in VALID_INTENTS:
            intent = parsed["intent"]
    except Exception as e:  # noqa: BLE001
        logger.error("[chat] 意图分类失败，回退 knowledge_qa: %s", e)

    logger.info("[chat] intent: %s | message: %s", intent, message[:30])
    await emit({"type": "intent", "intent": intent})
    return {"intent": intent}
