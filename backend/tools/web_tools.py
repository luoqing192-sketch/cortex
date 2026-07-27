"""网络研究工具（新增能力）：

- web_search(query, max_results)  —— DuckDuckGo 搜索，返回 [{title, url, snippet}]
- fetch_webpage(url)              —— 抓取网页并抽取正文（trafilatura，回退 BeautifulSoup）

配套 OpenAI function-calling schema 供 web_research 节点绑定。
"""
from __future__ import annotations

import httpx

from logger import logger

MAX_PAGE_CHARS = 8000
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CortexBot/1.0; +https://example.local)"
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "联网搜索。输入查询词，返回若干条 {title, url, snippet}。用于查最新信息或找到相关网页。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "max_results": {"type": "integer", "description": "返回结果数，默认 5，最多 10"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "抓取给定 URL 的网页并抽取正文文本。用于阅读搜索到的网页或用户直接给出的链接。",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "要抓取的网页完整 URL"}},
                "required": ["url"],
            },
        },
    },
]


def _ddgs():
    """兼容新旧包名：ddgs（新）/ duckduckgo_search（旧）。"""
    try:
        from ddgs import DDGS  # type: ignore
        return DDGS
    except Exception:  # noqa: BLE001
        try:
            from duckduckgo_search import DDGS  # type: ignore
            return DDGS
        except Exception as e:  # noqa: BLE001
            logger.error("DuckDuckGo 库未安装: %s", e)
            return None


def web_search(query: str, max_results: int = 5) -> dict:
    max_results = max(1, min(int(max_results or 5), 10))
    ddgs_cls = _ddgs()
    if ddgs_cls is None:
        return {"error": "搜索库未安装（pip install ddgs）", "results": []}
    try:
        results = []
        with ddgs_cls() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title") or "",
                        "url": r.get("href") or r.get("url") or "",
                        "snippet": r.get("body") or r.get("snippet") or "",
                    }
                )
        logger.info("[web_search] '%s' → %d 条", query[:40], len(results))
        return {"results": results, "total": len(results)}
    except Exception as e:  # noqa: BLE001
        logger.error("[web_search] 失败: %s", e)
        return {"error": f"搜索失败: {e}", "results": []}


def _extract_main_text(html: str, url: str) -> str:
    # 优先 trafilatura（对文档/文章正文提取效果好）
    try:
        import trafilatura

        extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=True)
        if extracted:
            return extracted
    except Exception:  # noqa: BLE001
        pass
    # 回退 BeautifulSoup 纯文本
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        return "\n".join(line for line in text.splitlines() if line.strip())
    except Exception:  # noqa: BLE001
        return ""


def fetch_webpage(url: str) -> dict:
    if not url or not url.startswith(("http://", "https://")):
        return {"error": "无效的 URL（需以 http:// 或 https:// 开头）"}
    try:
        with httpx.Client(follow_redirects=True, timeout=20, headers=HTTP_HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
        text = _extract_main_text(html, url)
        if not text:
            return {"error": "未能从该页面抽取正文", "url": url}
        truncated = len(text) > MAX_PAGE_CHARS
        logger.info("[fetch_webpage] %s → %d 字符%s", url[:60], len(text), "(截断)" if truncated else "")
        return {
            "url": url,
            "content": text[:MAX_PAGE_CHARS],
            "truncated": truncated,
            "length": len(text),
        }
    except Exception as e:  # noqa: BLE001
        logger.error("[fetch_webpage] 失败 %s: %s", url, e)
        return {"error": f"抓取失败: {e}", "url": url}


def execute_web_tool(name: str, args: dict) -> dict:
    if name == "web_search":
        return web_search(args.get("query", ""), args.get("max_results", 5))
    if name == "fetch_webpage":
        return fetch_webpage(args.get("url", ""))
    return {"error": f"Unknown web tool: {name}"}
