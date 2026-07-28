"""CLI 配置与凭据管理。

- 配置：~/.cortex/config.toml（api_url / mode / last_conversation / 渲染偏好）
- 凭据：keyring 优先，回退 ~/.cortex/credentials（600）
- 覆盖优先级：环境变量 > 配置文件 > 默认值
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

try:
    import tomllib  # py>=3.11
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

def _config_dir() -> Path:
    # 每次调用读环境变量，便于测试隔离与运行期覆盖
    return Path(os.environ.get("CORTEX_HOME", Path.home() / ".cortex"))


class _LazyPath:
    """按需解析的路径代理，兼容属性式访问（CONFIG_FILE.exists() 等）。"""

    def __init__(self, name: str):
        self._name = name

    def _resolve(self) -> Path:
        return _config_dir() / self._name

    def __getattr__(self, item):
        return getattr(self._resolve(), item)

    def __fspath__(self):
        return str(self._resolve())

    def __truediv__(self, other):
        return self._resolve() / other

    def __str__(self):
        return str(self._resolve())


CONFIG_FILE = _LazyPath("config.toml")
CRED_FILE = _LazyPath("credentials")

DEFAULTS = {
    "api_url": "http://localhost:8000",
    "mode": "remote",  # remote | local
    "last_conversation": None,
}

_KEYRING_SERVICE = "cortex-cli"


def _ensure_dir() -> None:
    _config_dir().mkdir(parents=True, exist_ok=True)


def _dump_toml(data: dict) -> str:
    """极简 TOML 写出（仅平坦 str/int/bool/None），避免额外依赖。"""
    lines = []
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        else:
            esc = str(v).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k} = "{esc}"')
    return "\n".join(lines) + "\n"


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "rb") as f:
                cfg.update(tomllib.load(f))
        except Exception:
            pass
    # 环境变量覆盖
    if os.environ.get("CORTEX_API_URL"):
        cfg["api_url"] = os.environ["CORTEX_API_URL"]
    if os.environ.get("CORTEX_MODE"):
        cfg["mode"] = os.environ["CORTEX_MODE"]
    return cfg


def save_config(cfg: dict) -> None:
    _ensure_dir()
    persist = {k: v for k, v in cfg.items() if k in DEFAULTS}
    CONFIG_FILE.write_text(_dump_toml(persist), encoding="utf-8")


def get_setting(key: str):
    return load_config().get(key)


def set_setting(key: str, value) -> None:
    cfg = load_config()
    if value in ("", "none", "null"):
        value = None
    cfg[key] = value
    save_config(cfg)


# ---------------- 凭据 ----------------
def _cred_key(api_url: str) -> str:
    return api_url or DEFAULTS["api_url"]


def save_token(api_url: str, token: str) -> None:
    try:
        import keyring

        keyring.set_password(_KEYRING_SERVICE, _cred_key(api_url), token)
        return
    except Exception:
        pass
    # 回退文件（600）
    _ensure_dir()
    lines = _read_cred_file()
    lines[_cred_key(api_url)] = token
    CRED_FILE.write_text(
        "".join(f"{k}\t{v}\n" for k, v in lines.items()), encoding="utf-8"
    )
    try:
        CRED_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def load_token(api_url: str) -> str | None:
    if os.environ.get("CORTEX_TOKEN"):
        return os.environ["CORTEX_TOKEN"]
    try:
        import keyring

        tok = keyring.get_password(_KEYRING_SERVICE, _cred_key(api_url))
        if tok:
            return tok
    except Exception:
        pass
    return _read_cred_file().get(_cred_key(api_url))


def delete_token(api_url: str) -> None:
    try:
        import keyring

        keyring.delete_password(_KEYRING_SERVICE, _cred_key(api_url))
    except Exception:
        pass
    lines = _read_cred_file()
    if _cred_key(api_url) in lines:
        del lines[_cred_key(api_url)]
        CRED_FILE.write_text(
            "".join(f"{k}\t{v}\n" for k, v in lines.items()), encoding="utf-8"
        )


def _read_cred_file() -> dict:
    out: dict = {}
    if CRED_FILE.exists():
        for line in CRED_FILE.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                k, v = line.split("\t", 1)
                out[k] = v
    return out
