#!/usr/bin/env python3
"""
手搓 Tool-Call Wiki Agent —— 最小完整版

核心思路：
  1. 定义 4 个本地函数（list / read / search / write）
  2. 把它们的"使用说明书"（OpenAI tool schema）发给 LLM
  3. LLM 返回想调的工具名+参数 → 你执行 → 把结果塞回 messages
  4. 循环，直到 LLM 不再要工具，直接给最终答案

依赖：
    pip install requests

用法：
    # 1. 启动 Ollama 并拉模型
    ollama serve &
    ollama pull qwen2.5:7b

    # 2. 跑 agent
    python wiki_agent.py "扫描本目录所有 md，按主题分类生成 INDEX.md"

    # 也可改成 OpenAI / OpenClaw / 阿里百炼，只要是 OpenAI 兼容协议就行
"""

import json
import os
import sys
from pathlib import Path

import requests

# ════════════════════════════════════════════════════════════════════
#   配置
# ════════════════════════════════════════════════════════════════════
WORK_DIR = Path(os.environ.get("WIKI_DIR", Path.home() / "Documents" / "qingluo")).resolve()

# OpenAI 兼容端点 —— 改这两行就能切到任何兼容服务
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "http://localhost:11434/v1/chat/completions")
LLM_MODEL    = os.environ.get("LLM_MODEL",    "qwen2.5:7b")
LLM_API_KEY  = os.environ.get("LLM_API_KEY",  "ollama")  # Ollama 不验证，随便填

MAX_STEPS = 20    # 防死循环
MAX_READ  = 8000  # 单次读文件最大字符数（防爆上下文）


# ════════════════════════════════════════════════════════════════════
#   工具实现（4 个函数）
# ════════════════════════════════════════════════════════════════════
def _safe_path(rel_path: str) -> Path:
    """把相对路径解析成绝对路径，且必须落在 WORK_DIR 内（防越界写）"""
    p = (WORK_DIR / rel_path).resolve()
    if not str(p).startswith(str(WORK_DIR)):
        raise ValueError(f"path escapes WORK_DIR: {rel_path}")
    return p


def list_files(pattern: str = "**/*.md") -> str:
    """列出匹配 glob 的文件，相对路径"""
    files = sorted(
        str(p.relative_to(WORK_DIR))
        for p in WORK_DIR.glob(pattern)
        if p.is_file() and ".bak" not in p.name
    )
    return "\n".join(files) if files else "(no files)"


def read_file(path: str, max_chars: int = MAX_READ) -> str:
    """读文件，超长截断"""
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: {path} not found"
    text = p.read_text(encoding="utf-8", errors="ignore")
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n...[truncated, total {len(text)} chars]"
    return text


def search_in_files(keyword: str, glob_pattern: str = "**/*.md") -> str:
    """关键词搜索，返回 file:line: snippet（最多 50 条）"""
    hits = []
    for p in WORK_DIR.glob(glob_pattern):
        if not p.is_file():
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if keyword.lower() in line.lower():
                    rel = p.relative_to(WORK_DIR)
                    hits.append(f"{rel}:{i}: {line.strip()[:120]}")
                    if len(hits) >= 50:
                        return "\n".join(hits) + "\n...[more hits truncated]"
        except Exception:
            pass
    return "\n".join(hits) if hits else "(no match)"


def write_file(path: str, content: str) -> str:
    """写文件；如果目标已存在，先备份到 .bak"""
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        backup = p.with_suffix(p.suffix + ".bak")
        backup.write_text(p.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    p.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content)} chars to {path}" + (
        " (backup created)" if (p.with_suffix(p.suffix + ".bak")).exists() else ""
    )


TOOL_REGISTRY = {
    "list_files": list_files,
    "read_file": read_file,
    "search_in_files": search_in_files,
    "write_file": write_file,
}


# ════════════════════════════════════════════════════════════════════
#   工具的"使用说明书"——OpenAI tool schema
#   LLM 看到这个就知道有哪些工具、每个工具要哪些参数
# ════════════════════════════════════════════════════════════════════
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List markdown files in the wiki directory matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob like '**/*.md' or 'interview*.md'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's content. Path is relative to wiki root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "description": "default 8000"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_files",
            "description": "Case-insensitive keyword search across files. Returns 'file:line: snippet' lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "glob_pattern": {"type": "string", "description": "default '**/*.md'"},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (overwrites). Existing file is auto-backed up to <file>.bak. Use this to create or update wiki pages like INDEX.md.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


# ════════════════════════════════════════════════════════════════════
#   System prompt —— 教 LLM 怎么用这些工具
# ════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = f"""You are a wiki maintainer agent working in: {WORK_DIR}

Available tools: list_files, read_file, search_in_files, write_file.

Workflow guidance:
1. Always start by calling list_files to see what exists.
2. Use read_file or search_in_files to inspect content before deciding.
3. When generating an INDEX/TOC, group files by topic (resume / interview / recsys / health / scripts / others).
   For each file, give a one-line Chinese summary based on its actual content.
4. Use write_file to save the result. Path 'INDEX.md' writes to the wiki root.
5. When you finish, reply with a brief Chinese summary of what you changed (NO tool call).

Be concise. Do not read the same file twice. If a file is huge, just read the top section."""


# ════════════════════════════════════════════════════════════════════
#   主循环
# ════════════════════════════════════════════════════════════════════
def call_llm(messages):
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    resp = requests.post(
        LLM_ENDPOINT,
        headers=headers,
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
            "temperature": 0.3,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


def run_agent(user_task: str):
    print(f"WORK_DIR  = {WORK_DIR}")
    print(f"LLM       = {LLM_MODEL} @ {LLM_ENDPOINT}")
    print(f"TASK      = {user_task}\n" + "─" * 70)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_task},
    ]

    for step in range(1, MAX_STEPS + 1):
        msg = call_llm(messages)
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []

        # 没有 tool_call → 终止
        if not tool_calls:
            print("\n" + "═" * 70)
            print("【最终回答】\n" + (msg.get("content") or "(empty)"))
            print("═" * 70)
            return

        # 执行所有 tool_call
        for tc in tool_calls:
            fname = tc["function"]["name"]
            try:
                fargs = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                fargs = {}

            print(f"[step {step}] → {fname}({json.dumps(fargs, ensure_ascii=False)[:120]})")

            try:
                fn = TOOL_REGISTRY[fname]
                result = fn(**fargs)
            except Exception as e:
                result = f"ERROR: {type(e).__name__}: {e}"

            print(f"          result: {str(result)[:200].replace(chr(10), ' / ')}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    print("\n[!] hit MAX_STEPS, stopping.")


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "扫描本目录所有 markdown 文档，按主题分类生成 INDEX.md，每个文档配 1 行中文摘要。"
    run_agent(task)
