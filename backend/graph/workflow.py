"""构建 LangGraph workflow：classify → 条件路由 → 4 个终端节点。"""
from langgraph.graph import END, StateGraph

from graph.nodes.casual_chat import casual_chat_node
from graph.nodes.classify import classify_node
from graph.nodes.generate_page import generate_page_node
from graph.nodes.knowledge_qa import knowledge_qa_node
from graph.nodes.web_research import web_research_node
from graph.state import GraphState

_ROUTES = {
    "knowledge_qa": "knowledge_qa",
    "generate_page": "generate_page",
    "web_research": "web_research",
    "casual_chat": "casual_chat",
}


def _route(state: GraphState) -> str:
    return _ROUTES.get(state.get("intent", "knowledge_qa"), "knowledge_qa")


def build_workflow():
    g = StateGraph(GraphState)
    g.add_node("classify", classify_node)
    g.add_node("knowledge_qa", knowledge_qa_node)
    g.add_node("generate_page", generate_page_node)
    g.add_node("web_research", web_research_node)
    g.add_node("casual_chat", casual_chat_node)

    g.set_entry_point("classify")
    g.add_conditional_edges("classify", _route, _ROUTES)
    for node in ("knowledge_qa", "generate_page", "web_research", "casual_chat"):
        g.add_edge(node, END)

    return g.compile()


workflow = build_workflow()
