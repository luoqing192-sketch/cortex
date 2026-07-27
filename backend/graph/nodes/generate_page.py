"""页面生成节点：代码生成 tool-call 循环 + 动态预览。"""
from graph.agent_loop import run_tool_loop, stream_final, to_lc_messages
from graph.prompts import CODE_GENERATION_PROMPT
from graph.state import GraphState
from llm import build_chat
from tools.code_generator import TOOL_DEFINITIONS, execute_tool_call


async def generate_page_node(state: GraphState) -> dict:
    emit = state["emit"]
    settings = state["settings"]
    history = state.get("history", [])
    active_prompt = state.get("active_prompt", "")
    conversation_id = str(state["conversation_id"])

    system_message = (active_prompt or "") + CODE_GENERATION_PROMPT
    messages = to_lc_messages(system_message, history)

    tracker = {"generated": False, "last_file": "index.html"}

    def on_tool(name: str, args: dict, _result: dict) -> None:
        if name == "generate_code":
            tracker["generated"] = True
            if args.get("file_path"):
                tracker["last_file"] = args["file_path"]

    def execute(name: str, args: dict) -> dict:
        return execute_tool_call(name, args, conversation_id)

    chat_tools = build_chat(settings, streaming=False).bind_tools(TOOL_DEFINITIONS)
    messages = await run_tool_loop(chat_tools, messages, execute, emit, max_iters=10, on_tool=on_tool)

    # 最终流式回答（无工具）
    chat = build_chat(settings, streaming=True)
    full = await stream_final(chat, messages, emit)

    if tracker["generated"]:
        preview_url = f"/preview/{conversation_id}/{tracker['last_file']}"
        await emit({"type": "preview", "url": preview_url})

    return {"full_response": full}
