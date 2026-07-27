#!/usr/bin/env python3
"""
Wiki Query Agent —— 让大模型查 wiki + 整理输出 + 带引用

和 wiki_agent.py 共用工具实现，只暴露"只读"工具集；
通过严格的 system prompt 强制带引用、不准编。

用法：
    python wiki_query.py "我简历里推荐系统部分写了哪些核心成果？"
    python wiki_query.py "面试题里关于 iGraph 有哪些考点？"

    # 切到本机 OpenClaw + qwen3.7-max（强推，比 7b 准很多）
    LLM_ENDPOINT=http://localhost:8788/v1/chat/completions \\
    LLM_MODEL=alibaba-bailian/qwen3.7-max \\
    LLM_API_KEY=$OPENCLAW_TOKEN \\
    python wiki_query.py "..."
"""

import json
import os
import sys
from pathlib import Path

import requests

WORK_DIR = Path(os.environ.get("WIKI_DIR", Path.home() / "Documents" / "qingluo")).resolve()
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "http://localhost:11434/v1/chat/completions")
LLM_MODEL    = os.environ.get("LLM_MODEL",    "qwen2.5:7b")
LLM_API_KEY  = os.environ.get("LLM_API_KEY",  "ollama")

MAX_STEPS = 12
MAX_READ  = 6000


# ════════════════════════════════════════════════════════════════════
#   只读工具（写工具被刻意去掉）
# ════════════════════════════════════════════════════════════════════
def _safe_path(rel: str) -> Path:
    p = (WORK_DIR / rel).resolve()
    if not str(p).startswith(str(WORK_DIR)):
        raise ValueError(f"path escapes WORK_DIR: {rel}")
    return p


def list_files(pattern: str = "**/*.md") -> str:
    files = sorted(
        str(p.relative_to(WORK_DIR))
        for p in WORK_DIR.glob(pattern)
        if p.is_file() and ".bak" not in p.name
    )
    return "\n".join(files) if files else "(no files)"


def read_file(path: str, start_line: int = 1, max_lines: int = 200) -> str:
    """按行读，返回 'L<n>: <line>' 格式 —— 关键：让 LLM 能精确引用行号"""
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: {path} not found"
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    end = min(start_line + max_lines - 1, len(lines))
    snippet = [f"L{i}: {lines[i-1]}" for i in range(start_line, end + 1)]
    head = f"# {path} (lines {start_line}-{end} of {len(lines)})\n"
    return head + "\n".join(snippet)


def search_in_files(keyword: str, glob_pattern: str = "**/*.md", max_hits: int = 30) -> str:
    """grep 风格 + 上下文，返回 path:line + 片段，方便 LLM 直接引用"""
    hits = []
    for p in WORK_DIR.glob(glob_pattern):
        if not p.is_file() or ".bak" in p.name:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if keyword.lower() in line.lower():
                    rel = p.relative_to(WORK_DIR)
                    hits.append(f"{rel}:L{i}: {line.strip()[:140]}")
                    if len(hits) >= max_hits:
                        return "\n".join(hits) + f"\n...[more, capped at {max_hits}]"
        except Exception:
            pass
    return "\n".join(hits) if hits else "(no match)"


TOOL_REGISTRY = {
    "list_files": list_files,
    "read_file": read_file,
    "search_in_files": search_in_files,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List wiki files matching a glob.",
            "parameters": {"type": "object", "properties": {
                "pattern": {"type": "string"},
            }},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_files",
            "description": "Keyword search across wiki, returns 'path:Lline: snippet'. USE THIS FIRST for any factual question.",
            "parameters": {"type": "object", "properties": {
                "keyword": {"type": "string"},
                "glob_pattern": {"type": "string"},
                "max_hits": {"type": "integer"},
            }, "required": ["keyword"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a slice of a file by line range. Use after search_in_files locates a hit.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "max_lines": {"type": "integer"},
            }, "required": ["path"]},
        },
    },
]


# ════════════════════════════════════════════════════════════════════
#   System prompt —— 强制引用 + 不准编
# ════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = f"""You are a wiki query assistant. Working directory: {WORK_DIR}

Goal: Answer the user's question using ONLY information from the wiki files.

Workflow:
1. Decompose the question into 1–3 keywords.
2. Call search_in_files with each keyword to locate relevant lines.
3. For each promising hit, call read_file with start_line near the hit (e.g. start_line = hit_line - 5, max_lines = 40) to get full context.
4. If first round of search misses, try synonyms / English/Chinese variants.
5. After enough evidence, stop calling tools and answer in Chinese.

Output format (STRICT):
  ## 答案
  <one paragraph, direct answer to the question>

  ## 关键要点
  - <point 1> [来源: filename:Lstart-Lend]
  - <point 2> [来源: filename:Lstart-Lend]

  ## 引用
  - filename:Lstart-Lend  — <one-line reason>

Rules:
- Every factual claim MUST carry a [来源: ...] citation.
- If wiki has NO relevant content, say "wiki 中未找到相关内容" — DO NOT make things up.
- Cite line ranges, not the whole file.
- Be concise; quote at most 2 short snippets verbatim."""


# ════════════════════════════════════════════════════════════════════
#   主循环（流式打印，体感更好）
# ════════════════════════════════════════════════════════════════════
def call_llm(messages, stream=False):
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    resp = requests.post(
        LLM_ENDPOINT, headers=headers,
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
            "temperature": 0.2,
            "stream": stream,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


def query(user_question: str):
    print(f"WIKI = {WORK_DIR}")
    print(f"LLM  = {LLM_MODEL}")
    print(f"Q    = {user_question}\n" + "─" * 70)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_question},
    ]

    for step in range(1, MAX_STEPS + 1):
        msg = call_llm(messages)
        messages.append(msg)
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            print("\n" + "═" * 70)
            print(msg.get("content") or "(empty answer)")
            print("═" * 70)
            return msg.get("content")

        for tc in tool_calls:
            fname = tc["function"]["name"]
            try:
                fargs = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                fargs = {}
            print(f"[step {step}] → {fname}({json.dumps(fargs, ensure_ascii=False)[:120]})")
            try:
                result = TOOL_REGISTRY[fname](**fargs)
            except Exception as e:
                result = f"ERROR: {type(e).__name__}: {e}"
            preview = str(result).replace("\n", " / ")[:200]
            print(f"          ↳ {preview}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    print("\n[!] hit MAX_STEPS")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "我简历里关于推荐系统的核心成果有哪些？"
    query(q)
