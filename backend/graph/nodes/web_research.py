"""网络研究节点（新增）：web_search + fetch_webpage 循环 → 来源 → 流式总结分析。"""
from graph.agent_loop import run_tool_loop, stream_final, to_lc_messages
from graph.prompts import WEB_RESEARCH_PROMPT
from graph.state import GraphState
from llm import build_chat
from tools.web_tools import TOOL_DEFINITIONS, execute_web_tool


async def web_research_node(state: GraphState) -> dict:
    emit = state["emit"]
    settings = state["settings"]
    history = state.get("history", [])
    active_prompt = state.get("active_prompt", "")

    system_message = (active_prompt or "") + "\n\n" + WEB_RESEARCH_PROMPT
    messages = to_lc_messages(system_message, history)

    sources: list[dict] = []
    seen_urls: set[str] = set()

    def on_tool(name: str, args: dict, result: dict) -> None:
        # 收集访问过的来源（去重）
        if name == "fetch_webpage" and not result.get("error"):
            url = result.get("url") or args.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append({"title": url, "url": url})
        if name == "web_search":
            for r in result.get("results", []):
                url = r.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({"title": r.get("title") or url, "url": url})

    def execute(name: str, args: dict) -> dict:
        return execute_web_tool(name, args)

    chat_tools = build_chat(settings, streaming=False).bind_tools(TOOL_DEFINITIONS)
    messages = await run_tool_loop(chat_tools, messages, execute, emit, max_iters=6, on_tool=on_tool)

    # 只保留实际抓取过正文的来源优先展示（fetch 成功的排前面）
    fetched = [s for s in sources if s["url"] in seen_urls]
    if fetched:
        await emit({"type": "sources", "sources": fetched[:8]})

    chat = build_chat(settings, streaming=True)
    full = await stream_final(chat, messages, emit)
    return {"full_response": full}
