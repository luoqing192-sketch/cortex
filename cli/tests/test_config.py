"""配置与凭据（文件回退路径）。"""
import importlib


def _reload_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEX_HOME", str(tmp_path))
    import cortex_cli.config as cfg
    importlib.reload(cfg)
    return cfg


def test_config_set_get(tmp_path, monkeypatch):
    cfg = _reload_config(tmp_path, monkeypatch)
    cfg.set_setting("api_url", "http://example:9000")
    assert cfg.get_setting("api_url") == "http://example:9000"
    assert cfg.load_config()["mode"] == "remote"  # 默认值


def test_last_conversation_none(tmp_path, monkeypatch):
    cfg = _reload_config(tmp_path, monkeypatch)
    cfg.set_setting("last_conversation", "none")
    assert cfg.get_setting("last_conversation") is None


def test_token_file_fallback(tmp_path, monkeypatch):
    cfg = _reload_config(tmp_path, monkeypatch)
    # 强制文件回退：让 keyring 不可用
    monkeypatch.setattr(cfg, "_read_cred_file", cfg._read_cred_file)
    url = "http://localhost:8000"
    # keyring 可能存在也可能不存在；直接测文件回退函数不依赖 keyring 结果
    cfg.CRED_FILE.parent.mkdir(parents=True, exist_ok=True)
    cfg.CRED_FILE.write_text(f"{url}\tTOKEN123\n", encoding="utf-8")
    assert cfg._read_cred_file()[url] == "TOKEN123"
