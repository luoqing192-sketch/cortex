"""CliRunner 冒烟：--version / --help / 无后端时报错友好。"""
from typer.testing import CliRunner

from cortex_cli.main import app

runner = CliRunner()


def test_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0 and "cortex-cli" in r.stdout


def test_help():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "chat" in r.stdout and "login" in r.stdout


def test_config_list(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEX_HOME", str(tmp_path))
    r = runner.invoke(app, ["config", "list"])
    # 注：get_console() 走独立 UTF-8 流，不进 CliRunner 捕获，故只断言退出码
    assert r.exit_code == 0


def test_config_set_get_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEX_HOME", str(tmp_path))
    assert runner.invoke(app, ["config", "set", "api_url", "http://h:1/"]).exit_code == 0
    import cortex_cli.config as cfg
    assert cfg.get_setting("api_url") == "http://h:1/"


def test_whoami_no_token(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEX_HOME", str(tmp_path))
    monkeypatch.delenv("CORTEX_TOKEN", raising=False)
    # 隔离 keyring：确保查不到 token
    import cortex_cli.config as cfg
    monkeypatch.setattr(cfg, "load_token", lambda _url: None)
    r = runner.invoke(app, ["whoami"])
    assert r.exit_code == 1
