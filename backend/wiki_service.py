"""Wiki 子进程服务：复用原 Python agent（wiki_query.py / wiki_agent.py）。

- search_knowledge / run_wiki_query：只读检索
- run_wiki_organize：整理（可写）

LLM 端点优先用 DEEPSEEK_API_KEY（若配置），否则回退到管理后台配置的主 LLM。
"""
import asyncio
import re
import subprocess
import sys

from config import DEEPSEEK_API_KEY, WIKI_DIR
from logger import logger

QUERY_SCRIPT = WIKI_DIR / "script" / "wiki_query.py"
AGENT_SCRIPT = WIKI_DIR / "script" / "wiki_agent.py"

_ANSWER_RE = re.compile(r"═{10,}\n([\s\S]*?)(?:\n═{10,}|$)")


def _wiki_env(settings: dict) -> dict:
    import os

    env = dict(os.environ)
    env["WIKI_DIR"] = str(WIKI_DIR)
    env["PYTHONIOENCODING"] = "utf-8"
    if DEEPSEEK_API_KEY:
        env["LLM_ENDPOINT"] = "https://api.deepseek.com/v1/chat/completions"
        env["LLM_MODEL"] = "deepseek-chat"
        env["LLM_API_KEY"] = DEEPSEEK_API_KEY
    else:
        # 回退：复用管理后台配置的主 LLM
        env["LLM_ENDPOINT"] = settings.get("llm_base_url") or "https://api.deepseek.com/v1/chat/completions"
        env["LLM_MODEL"] = settings.get("llm_model") or "deepseek-chat"
        env["LLM_API_KEY"] = settings.get("llm_api_key") or ""
    return env


def _run(script, arg: str, settings: dict, timeout: int) -> str:
    proc = subprocess.run(
        [sys.executable, str(script), arg],
        env=_wiki_env(settings),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return proc.stdout or ""


async def run_wiki_query(question: str, settings: dict) -> str:
    return await asyncio.to_thread(_run, QUERY_SCRIPT, question, settings, 120)


async def run_wiki_organize(task: str, settings: dict) -> str:
    return await asyncio.to_thread(_run, AGENT_SCRIPT, task, settings, 300)


async def search_knowledge(query: str, settings: dict) -> dict:
    """返回 {items: [...], fallback: bool}，对齐原 app.js searchKnowledge。"""
    if not QUERY_SCRIPT.exists():
        logger.error("[searchKnowledge] wiki_query.py 不存在")
        return {"items": [], "fallback": True}
    try:
        logger.info("[searchKnowledge] 调用 wiki_query.py: %s", query[:50])
        output = await run_wiki_query(query, settings)
        m = _ANSWER_RE.search(output)
        answer = (m.group(1).strip() if m else output.strip())
        if not answer or answer == "(empty answer)":
            logger.info("[searchKnowledge] 未找到相关内容")
            return {"items": [], "fallback": False}
        logger.info("[searchKnowledge] 返回 %d 字符", len(answer))
        return {
            "items": [{"title": "Wiki 知识库检索结果", "content": answer, "knowledge_base_name": "Wiki"}],
            "fallback": False,
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Wiki search error: %s", e)
        return {"items": [], "fallback": True}
