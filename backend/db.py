"""SQLite (aiosqlite) 数据访问层：连接、建表、默认数据、查询辅助。

表结构对齐原 llm_test 的 MySQL schema：users / conversations / messages / settings / prompts。
"""
import aiosqlite
import bcrypt

from config import DB_PATH
from logger import logger

_conn: aiosqlite.Connection | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT DEFAULT '新对话',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);

CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  setting_key TEXT UNIQUE NOT NULL,
  setting_value TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  is_active INTEGER DEFAULT 0,
  description TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
"""

DEFAULT_SETTINGS = [
    ("llm_base_url", "https://api.deepseek.com/v1/chat/completions"),
    ("llm_api_key", ""),
    ("llm_model", "deepseek-chat"),
    ("llm_temperature", "0.7"),
    ("llm_max_tokens", "4096"),
    ("llm_top_p", "0.9"),
]

DEFAULT_PROMPT = (
    "默认助手",
    "你是一个友好、专业的AI助手。请根据用户的问题提供准确、有帮助的回答。"
    "如果知识库中有相关信息，请优先参考知识库内容进行回答。",
    "默认的系统提示词",
)


async def get_conn() -> aiosqlite.Connection:
    global _conn
    if _conn is None:
        _conn = await aiosqlite.connect(DB_PATH)
        _conn.row_factory = aiosqlite.Row
        await _conn.execute("PRAGMA foreign_keys = ON")
        await _conn.commit()
    return _conn


async def close_conn() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    conn = await get_conn()
    async with conn.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    rows = await fetch_all(sql, params)
    return rows[0] if rows else None


async def execute(sql: str, params: tuple = ()) -> tuple[int, int]:
    """执行写操作，返回 (lastrowid, rowcount)。"""
    conn = await get_conn()
    cur = await conn.execute(sql, params)
    await conn.commit()
    return cur.lastrowid, cur.rowcount


async def init_db() -> None:
    conn = await get_conn()
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()

    # 默认设置（存在则忽略）
    for key, value in DEFAULT_SETTINGS:
        await conn.execute(
            "INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value),
        )

    # 默认 prompt（仅当没有任何 prompt 时插入并激活）
    row = await fetch_one("SELECT COUNT(*) AS c FROM prompts")
    if not row or row["c"] == 0:
        await conn.execute(
            "INSERT INTO prompts (name, content, description, is_active) VALUES (?, ?, ?, 1)",
            (DEFAULT_PROMPT[0], DEFAULT_PROMPT[1], DEFAULT_PROMPT[2]),
        )

    await conn.commit()
    logger.info("✅ SQLite 初始化完成: %s", DB_PATH)


async def ensure_admin(username: str = "admin", password: str = "123456") -> None:
    existing = await fetch_one("SELECT id, username, role FROM users WHERE username = ?", (username,))
    if existing:
        logger.info("✅ Admin 已存在: %s (%s)", existing["username"], existing["role"])
        return
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()
    await execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, pw_hash, "admin"),
    )
    logger.info("✅ Admin 已创建: %s / %s", username, password)
