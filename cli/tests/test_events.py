"""事件解析：后端 SSE JSON → ChatEvent。"""
from cortex_cli.events import ChatEvent


def test_content_event():
    e = ChatEvent.from_sse({"content": "你好"})
    assert e.type == "content" and e.content == "你好"


def test_typed_events():
    assert ChatEvent.from_sse({"type": "intent", "intent": "web_research"}).data["intent"] == "web_research"
    assert ChatEvent.from_sse({"type": "tool_progress", "tool": "web_search", "status": "running"}).data["status"] == "running"
    assert ChatEvent.from_sse({"type": "sources", "sources": [{"url": "x"}]}).data["sources"][0]["url"] == "x"
    assert ChatEvent.from_sse({"type": "preview", "url": "/p/1/index.html"}).data["url"].endswith("index.html")


def test_error_event():
    e = ChatEvent.from_sse({"error": "boom"})
    assert e.type == "error" and e.data["message"] == "boom"
