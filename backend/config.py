"""集中配置：按 backend/ 目录加载 .env，暴露常量与路径。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# 按脚本所在目录加载 .env，与 cwd 解耦
load_dotenv(BASE_DIR / ".env")

PORT = int(os.environ.get("PORT", 8000))

JWT_SECRET = os.environ.get("JWT_SECRET", "cortex-dev-secret-change-me")
JWT_EXPIRES_IN = os.environ.get("JWT_EXPIRES_IN", "30d")
JWT_ALGORITHM = "HS256"

DB_PATH = str(BASE_DIR / os.environ.get("DB_PATH", "cortex.db"))

LLM_MAX_CONCURRENT = int(os.environ.get("LLM_MAX_CONCURRENT", 5))
LLM_REQUEST_TIMEOUT = int(os.environ.get("LLM_REQUEST_TIMEOUT", 60))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

WIKI_DIR = BASE_DIR / "wiki"
DEMO_CODE_DIR = BASE_DIR / "demo_code"
UPLOADS_DIR = BASE_DIR / "uploads"
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

# 确保运行期目录存在
DEMO_CODE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def expires_seconds() -> int:
    """把 '30d' / '12h' / '3600' 之类解析成秒数。"""
    v = (JWT_EXPIRES_IN or "").strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if v and v[-1] in units:
        try:
            return int(v[:-1]) * units[v[-1]]
        except ValueError:
            pass
    try:
        return int(v)
    except ValueError:
        return 30 * 86400
