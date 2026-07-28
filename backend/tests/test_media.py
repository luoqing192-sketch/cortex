"""backend/media.py：多模态 content 构造。"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from media import build_multimodal_content, is_image, image_url_block  # noqa: E402


def test_no_images_returns_plain_text():
    assert build_multimodal_content("你好", None) == "你好"
    assert build_multimodal_content("你好", []) == "你好"
    assert build_multimodal_content("你好", [{"type": "file", "url": "x"}]) == "你好"


def test_is_image():
    assert is_image({"type": "image"})
    assert is_image({"mime": "image/png"})
    assert not is_image({"type": "file", "mime": "text/plain"})


def test_http_url_block():
    b = image_url_block({"type": "image", "url": "https://x/y.png"})
    assert b["type"] == "image_url" and b["image_url"]["url"] == "https://x/y.png"


def test_data_uri_from_path(tmp_path):
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    p = tmp_path / "dot.png"
    p.write_bytes(png)
    content = build_multimodal_content("看图", [{"type": "image", "path": str(p)}])
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
