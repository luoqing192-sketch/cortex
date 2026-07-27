"""闲聊拒绝节点。"""
from graph.prompts import CASUAL_CHAT_REJECT
from graph.state import GraphState


async def casual_chat_node(state: GraphState) -> dict:
    emit = state["emit"]
    await emit({"content": CASUAL_CHAT_REJECT})
    return {"full_response": CASUAL_CHAT_REJECT}
