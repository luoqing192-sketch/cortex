"""知识问答节点：wiki 检索 + 流式回答。"""
from graph.agent_loop import stream_final, to_lc_messages
from graph.state import GraphState
from llm import build_chat
from logger import logger
from wiki_service import search_knowledge


async def knowledge_qa_node(state: GraphState) -> dict:
    emit = state["emit"]
    settings = state["settings"]
    message = state["user_message"]
    history = state.get("history", [])
    active_prompt = state.get("active_prompt", "")

    knowledge_items = []
    fallback = False
    try:
        result = await search_knowledge(message, settings)
        knowledge_items = result["items"]
        fallback = result["fallback"]
    except Exception as e:  # noqa: BLE001
        logger.error("Knowledge search error: %s", e)
        fallback = True

    system_message = active_prompt or ""
    if knowledge_items:
        system_message += "\n\n以下是从知识库中检索到的相关信息，请参考这些信息来回答用户的问题：\n\n"
        for i, item in enumerate(knowledge_items):
            system_message += (
                f"【知识 {i + 1}】\n标题：{item['title']}\n内容：{item['content']}\n"
                f"来源：{item['knowledge_base_name']}\n\n"
            )

    if fallback:
        await emit({"type": "notice", "message": "知识库检索失败，本次回答未参考知识库内容"})

    chat = build_chat(settings, streaming=True)
    messages = to_lc_messages(system_message, history)
    full = await stream_final(chat, messages, emit)
    return {"full_response": full}
