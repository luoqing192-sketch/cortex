"""代码生成工具 —— 移植自 llm_test/tools/code-generator.js。

提供 6 个 OpenAI function-calling 兼容工具，在隔离目录 demo_code/{conversationId} 内操作：
search_codebase / read_file / get_project_structure / get_symbol_definition / generate_code / run_command
"""
import re
import subprocess
from pathlib import Path

from config import DEMO_CODE_DIR

# ============================================================
# Tool schema（OpenAI function-calling 格式）
# ============================================================
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_codebase",
            "description": "搜索当前项目代码库中的相关代码片段，用于发现相关类、接口、依赖",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "file_pattern": {"type": "string", "description": "文件匹配模式，如 *.tsx, *.js"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容，支持按行范围读取",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径（相对于项目根目录）"},
                    "start_line": {"type": "integer", "description": "起始行号（1-based）"},
                    "end_line": {"type": "integer", "description": "结束行号（1-based，包含）"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_structure",
            "description": "获取项目目录结构，以树形格式展示",
            "parameters": {
                "type": "object",
                "properties": {"depth": {"type": "integer", "description": "目录遍历深度，默认为3"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_symbol_definition",
            "description": "查找代码中的符号定义，如函数、类、接口、类型等",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_name": {"type": "string", "description": "要查找的符号名称"},
                    "file_path": {"type": "string", "description": "限定搜索的文件路径（可选）"},
                },
                "required": ["symbol_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": "生成或修改代码文件，支持创建、追加、插入、替换模式",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "目标文件路径（相对于项目根目录）"},
                    "content": {"type": "string", "description": "要写入的代码内容"},
                    "mode": {
                        "type": "string",
                        "enum": ["create", "append", "insert", "replace"],
                        "description": "写入模式: create-创建新文件, append-追加, insert-插入到指定行, replace-替换行范围",
                    },
                    "insert_position": {"type": "integer", "description": "insert 模式下的插入行号（1-based）"},
                    "replace_start": {"type": "integer", "description": "replace 模式起始行（1-based）"},
                    "replace_end": {"type": "integer", "description": "replace 模式结束行（1-based，包含）"},
                },
                "required": ["file_path", "content", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "在项目目录中执行 shell 命令（仅允许安全命令）",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "working_directory": {"type": "string", "description": "工作目录（相对于项目根目录，可选）"},
                },
                "required": ["command"],
            },
        },
    },
]

ALLOWED_COMMANDS = {"ls", "cat", "find", "node", "npm", "npx", "echo", "mkdir"}
MAX_SEARCH_RESULTS = 50


# ============================================================
# 安全 & 辅助
# ============================================================
def _base_dir(conversation_id: str) -> Path:
    base = DEMO_CODE_DIR / str(conversation_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_path(base_dir: Path, relative_path: str) -> Path | None:
    resolved = (base_dir / relative_path).resolve()
    base_resolved = base_dir.resolve()
    if resolved == base_resolved or str(resolved).startswith(str(base_resolved) + "/") \
            or str(resolved).startswith(str(base_resolved) + "\\"):
        return resolved
    return None


def _all_files(base_dir: Path) -> list[Path]:
    out = []
    for p in base_dir.rglob("*"):
        if any(part in ("node_modules", ".git") for part in p.parts):
            continue
        if p.is_file():
            out.append(p)
    return out


def _match_pattern(filename: str, pattern: str) -> bool:
    regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.fullmatch(regex, filename, re.IGNORECASE) is not None


def _escape_regex(s: str) -> str:
    return re.escape(s)


# ============================================================
# 工具入口
# ============================================================
def execute_tool_call(name: str, args: dict, conversation_id: str) -> dict:
    base_dir = _base_dir(conversation_id)
    if name == "search_codebase":
        return _search_codebase(base_dir, args)
    if name == "read_file":
        return _read_file(base_dir, args)
    if name == "get_project_structure":
        return _get_project_structure(base_dir, args)
    if name == "get_symbol_definition":
        return _get_symbol_definition(base_dir, args)
    if name == "generate_code":
        return _generate_code(base_dir, args)
    if name == "run_command":
        return _run_command(base_dir, args)
    return {"error": f"Unknown tool: {name}"}


# ============================================================
# 实现
# ============================================================
def _search_codebase(base_dir: Path, args: dict) -> dict:
    query = args.get("query", "")
    file_pattern = args.get("file_pattern")
    results = []
    ql = query.lower()
    for fp in _all_files(base_dir):
        if file_pattern and not _match_pattern(fp.name, file_pattern):
            continue
        try:
            lines = fp.read_text(encoding="utf-8", errors="ignore").split("\n")
        except Exception:
            continue
        for i, line in enumerate(lines):
            if ql in line.lower():
                results.append({"file": str(fp.relative_to(base_dir)), "line": i + 1, "content": line.rstrip()})
                if len(results) >= MAX_SEARCH_RESULTS:
                    return {"results": results, "total": len(results), "truncated": True}
    return {"results": results, "total": len(results)}


def _read_file(base_dir: Path, args: dict) -> dict:
    resolved = _safe_path(base_dir, args.get("path", ""))
    if resolved is None:
        return {"error": "路径越界：不允许访问项目目录之外的文件"}
    if not resolved.exists():
        return {"error": f"File not found: {args.get('path')}"}
    try:
        lines = resolved.read_text(encoding="utf-8", errors="ignore").split("\n")
    except Exception as e:  # noqa: BLE001
        return {"error": f"读取文件失败: {e}"}
    total = len(lines)
    start = max(1, args.get("start_line") or 1)
    end = min(total, args.get("end_line") or total)
    return {"content": "\n".join(lines[start - 1:end]), "total_lines": total}


def _get_project_structure(base_dir: Path, args: dict) -> dict:
    max_depth = args.get("depth") or 3

    def build(d: Path, prefix: str, depth: int) -> str:
        if depth >= max_depth:
            return ""
        entries = [e for e in sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                   if e.name not in ("node_modules", ".git")]
        out = ""
        for i, e in enumerate(entries):
            last = i == len(entries) - 1
            connector = "└── " if last else "├── "
            child_prefix = "    " if last else "│   "
            if e.is_dir():
                out += f"{prefix}{connector}{e.name}/\n"
                out += build(e, prefix + child_prefix, depth + 1)
            else:
                out += f"{prefix}{connector}{e.name}\n"
        return out

    try:
        return {"structure": build(base_dir, "", 0)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"获取目录结构失败: {e}"}


def _detect_symbol_type(line: str) -> str:
    for kw in ("function", "class", "interface", "type", "const", "let", "var"):
        if re.search(rf"\b{kw}\b", line):
            return kw
    return "unknown"


def _get_symbol_definition(base_dir: Path, args: dict) -> dict:
    symbol = args.get("symbol_name", "")
    file_path = args.get("file_path")
    esc = _escape_regex(symbol)
    patterns = [
        re.compile(rf"export\s+(default\s+)?(const|function|class|interface|type|let|var)\s+{esc}\b", re.I),
        re.compile(rf"^\s*(async\s+)?function\s+{esc}\s*\(", re.I),
        re.compile(rf"^\s*(export\s+)?(default\s+)?class\s+{esc}\b", re.I),
        re.compile(rf"^\s*(export\s+)?interface\s+{esc}\b", re.I),
        re.compile(rf"^\s*(export\s+)?type\s+{esc}\b", re.I),
        re.compile(rf"^\s*(export\s+)?(const|let|var)\s+{esc}\b", re.I),
    ]
    if file_path:
        resolved = _safe_path(base_dir, file_path)
        if resolved is None:
            return {"error": "路径越界：不允许访问项目目录之外的文件"}
        files = [resolved]
    else:
        files = [f for f in _all_files(base_dir) if re.search(r"\.(js|ts|tsx|jsx)$", f.name)]

    definitions = []
    for fp in files:
        try:
            lines = fp.read_text(encoding="utf-8", errors="ignore").split("\n")
        except Exception:
            continue
        for i, line in enumerate(lines):
            if any(p.search(line) for p in patterns):
                definitions.append(
                    {"file": str(fp.relative_to(base_dir)), "line": i + 1, "symbol": symbol,
                     "type": _detect_symbol_type(line), "signature": line.strip()}
                )
    return {"definitions": definitions}


def _generate_code(base_dir: Path, args: dict) -> dict:
    resolved = _safe_path(base_dir, args.get("file_path", ""))
    if resolved is None:
        return {"error": "路径越界：不允许访问项目目录之外的文件"}
    content = args.get("content", "")
    mode = args.get("mode")
    try:
        if mode == "create":
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return {"success": True, "file_path": args.get("file_path"), "mode": mode,
                    "lines_affected": len(content.split("\n"))}
        if mode == "append":
            existing = resolved.read_text(encoding="utf-8") if resolved.exists() else ""
            resolved.write_text(existing + content, encoding="utf-8")
            return {"success": True, "file_path": args.get("file_path"), "mode": mode,
                    "lines_affected": len(content.split("\n"))}
        if mode == "insert":
            pos = args.get("insert_position")
            if not pos or pos < 1:
                return {"error": "insert 模式需要提供有效的 insert_position（>= 1）"}
            lines = resolved.read_text(encoding="utf-8").split("\n")
            insert_lines = content.split("\n")
            lines[pos - 1:pos - 1] = insert_lines
            resolved.write_text("\n".join(lines), encoding="utf-8")
            return {"success": True, "file_path": args.get("file_path"), "mode": mode,
                    "lines_affected": len(insert_lines)}
        if mode == "replace":
            rs, re_ = args.get("replace_start"), args.get("replace_end")
            if not rs or not re_ or rs < 1 or re_ < rs:
                return {"error": "replace 模式需要提供有效的 replace_start 和 replace_end"}
            lines = resolved.read_text(encoding="utf-8").split("\n")
            replace_lines = content.split("\n")
            lines[rs - 1:re_] = replace_lines
            resolved.write_text("\n".join(lines), encoding="utf-8")
            return {"success": True, "file_path": args.get("file_path"), "mode": mode,
                    "lines_affected": len(replace_lines)}
        return {"error": f"未知的写入模式: {mode}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"代码生成失败: {e}"}


def _run_command(base_dir: Path, args: dict) -> dict:
    command = args.get("command", "")
    cmd_name = command.strip().split()[0] if command.strip() else ""
    if cmd_name not in ALLOWED_COMMANDS:
        return {"error": f"命令不在白名单中，只允许: {', '.join(sorted(ALLOWED_COMMANDS))}"}
    cwd = base_dir
    if args.get("working_directory"):
        resolved = _safe_path(base_dir, args["working_directory"])
        if resolved is None:
            return {"error": "工作目录路径越界：不允许在项目目录之外执行命令"}
        cwd = resolved
    try:
        proc = subprocess.run(command, shell=True, cwd=str(cwd), capture_output=True,
                              text=True, timeout=30)
        return {"stdout": proc.stdout or "", "stderr": proc.stderr or "", "exitCode": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30s"}
    except Exception as e:  # noqa: BLE001
        return {"stdout": "", "stderr": str(e), "exitCode": 1}
