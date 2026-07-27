"""从 DB settings 动态构建 langchain-openai ChatOpenAI（OpenAI 兼容端点）。"""
from langchain_openai import ChatOpenAI

from db import fetch_all, fetch_one


async def get_settings() -> dict:
    rows = await fetch_all("SELECT setting_key, setting_value FROM settings")
    return {r["setting_key"]: r["setting_value"] for r in rows}


async def get_active_prompt() -> dict | None:
    return await fetch_one("SELECT * FROM prompts WHERE is_active = 1 LIMIT 1")


def _normalize_base_url(url: str | None) -> str | None:
    """DB 里存的是完整端点（.../v1/chat/completions），
    ChatOpenAI 需要 base（.../v1），会自行追加 /chat/completions。"""
    if not url:
        return url
    url = url.rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url


def build_chat(
    settings: dict,
    *,
    streaming: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
) -> ChatOpenAI:
    def _f(key, default):
        try:
            return float(settings.get(key) or default)
        except (TypeError, ValueError):
            return default

    def _i(key, default):
        try:
            return int(settings.get(key) or default)
        except (TypeError, ValueError):
            return default

    return ChatOpenAI(
        base_url=_normalize_base_url(settings.get("llm_base_url")),
        api_key=settings.get("llm_api_key") or "sk-none",
        model=settings.get("llm_model") or "gpt-3.5-turbo",
        temperature=temperature if temperature is not None else _f("llm_temperature", 0.7),
        max_tokens=max_tokens if max_tokens is not None else _i("llm_max_tokens", 4096),
        top_p=top_p if top_p is not None else _f("llm_top_p", 0.9),
        streaming=streaming,
        timeout=300,
        max_retries=0,
    )
