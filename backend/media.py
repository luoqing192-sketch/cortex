"""图片附件 → OpenAI 兼容 vision content block。

存磁盘+引用策略：附件里带 path（本地文件）或 url（可访问地址）。
- 有 http(s) url：直接用该 url（模型侧自行拉取）。
- 只有 path：读盘 base64 编码成 data-uri。
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from logger import logger

_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def is_image(attachment: dict) -> bool:
    if attachment.get("type") == "image":
        return True
    mime = attachment.get("mime") or ""
    return mime in _IMAGE_MIMES


def to_data_uri(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        logger.warning("[media] 图片不存在: %s", path)
        return None
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def image_url_block(attachment: dict) -> dict | None:
    """构造 {type:"image_url", image_url:{url}}，失败返回 None。"""
    url = attachment.get("url")
    if url and url.startswith(("http://", "https://", "data:")):
        return {"type": "image_url", "image_url": {"url": url}}
    path = attachment.get("path")
    if path:
        data_uri = to_data_uri(path)
        if data_uri:
            return {"type": "image_url", "image_url": {"url": data_uri}}
    return None


def build_multimodal_content(text: str, attachments: list[dict] | None) -> str | list:
    """把文本 + 图片附件构造成 content：
    - 无图片附件 → 返回纯字符串（保持与旧逻辑一致）
    - 有图片 → 返回 [{type:text}, {type:image_url}, ...]
    """
    images = [a for a in (attachments or []) if is_image(a)]
    if not images:
        return text
    blocks: list = [{"type": "text", "text": text}]
    for a in images:
        block = image_url_block(a)
        if block:
            blocks.append(block)
    return blocks if len(blocks) > 1 else text
