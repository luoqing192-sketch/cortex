"""统一事件类型 —— CLI 面向它编程，remote/local 两种 Engine 都产出它。

事件形状与后端 SSE 完全对齐：
  queue / intent / notice / tool_progress / preview / sources / content / error / done
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatEvent:
    type: str  # queue|intent|notice|tool_progress|preview|sources|content|error|done
    content: str = ""  # type == "content" 的增量文本
    data: dict = field(default_factory=dict)  # 其它类型载荷

    @classmethod
    def from_sse(cls, obj: dict) -> "ChatEvent":
        """把后端 SSE 的一个 JSON 对象转成 ChatEvent。"""
        etype = obj.get("type")
        if obj.get("error"):
            return cls(type="error", data={"message": obj["error"]})
        if etype is None and "content" in obj:
            return cls(type="content", content=obj.get("content") or "")
        if etype:
            data = {k: v for k, v in obj.items() if k != "type"}
            return cls(type=etype, content=obj.get("content", ""), data=data)
        # 兜底：未知形状
        return cls(type="content", content=obj.get("content") or "")


# 便捷构造
def content_event(text: str) -> ChatEvent:
    return ChatEvent(type="content", content=text)


def error_event(message: str) -> ChatEvent:
    return ChatEvent(type="error", data={"message": message})


DONE = ChatEvent(type="done")
