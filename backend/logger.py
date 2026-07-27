"""日志：同时输出终端 + 文件（app.log，10MB 轮转）。"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from config import BASE_DIR

LOG_FILE = BASE_DIR / "app.log"
MAX_BYTES = 10 * 1024 * 1024  # 10MB


def setup_logging() -> logging.Logger:
    root = logging.getLogger()
    if getattr(root, "_cortex_configured", False):
        return logging.getLogger("cortex")

    # Windows 控制台默认 GBK，会导致 emoji 日志抛 UnicodeEncodeError，这里强制 UTF-8
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=1, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # 降噪：第三方库只记 WARNING 以上
    for noisy in ("httpx", "httpcore", "urllib3", "openai", "trafilatura", "ddgs", "primp", "duckduckgo_search"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root._cortex_configured = True  # type: ignore[attr-defined]
    return logging.getLogger("cortex")


logger = setup_logging()
