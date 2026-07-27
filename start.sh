#!/usr/bin/env bash
# Cortex 一键启动脚本（Windows Git Bash / Linux / macOS）
# 用法: ./start.sh [port]
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PORT="${1:-8000}"

# ---- 选择 python 执行文件（venv 优先）----
if [ -f "$BACKEND/.venv/Scripts/python.exe" ]; then
  PY="$BACKEND/.venv/Scripts/python.exe"      # Windows
elif [ -f "$BACKEND/.venv/bin/python" ]; then
  PY="$BACKEND/.venv/bin/python"              # Linux/macOS
else
  echo "==> 创建虚拟环境..."
  if command -v uv >/dev/null 2>&1; then
    ( cd "$BACKEND" && uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt )
  else
    ( cd "$BACKEND" && python -m venv .venv )
    if [ -f "$BACKEND/.venv/Scripts/python.exe" ]; then PY="$BACKEND/.venv/Scripts/python.exe"; else PY="$BACKEND/.venv/bin/python"; fi
    "$PY" -m pip install -r "$BACKEND/requirements.txt"
  fi
  if [ -f "$BACKEND/.venv/Scripts/python.exe" ]; then PY="$BACKEND/.venv/Scripts/python.exe"; else PY="$BACKEND/.venv/bin/python"; fi
fi

# ---- 构建前端（若未构建）----
if [ ! -f "$FRONTEND/dist/index.html" ]; then
  echo "==> 构建前端..."
  ( cd "$FRONTEND" && npm install && npm run build )
fi

# ---- 启动后端（自动建库 + 托管前端 dist）----
echo "==> 启动 Cortex，端口 $PORT"
cd "$BACKEND"
exec "$PY" -m uvicorn main:app --host 0.0.0.0 --port "$PORT"
