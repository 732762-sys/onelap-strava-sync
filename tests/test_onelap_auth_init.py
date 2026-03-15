import pytest

from sync_onelap_strava.onelap_auth_init import run_onelap_auth_init


def test_run_onelap_auth_init_saves_credentials_to_env(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda _: "testuser")
    monkeypatch.setattr("getpass.getpass", lambda _: "testpass")

    env_file = tmp_path / ".env"
    run_onelap_auth_init(env_file)

    content = env_file.read_text(encoding="utf-8")
    assert "ONELAP_USERNAME=testuser" in content
    assert "ONELAP_PASSWORD=testpass" in content


def test_run_onelap_auth_init_updates_existing_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ONELAP_USERNAME=old\nSTRAVA_CLIENT_ID=abc\n", encoding="utf-8")

    monkeypatch.setattr("builtins.input", lambda _: "newuser")
    monkeypatch.setattr("getpass.getpass", lambda _: "newpass")

    run_onelap_auth_init(env_file)

    content = env_file.read_text(encoding="utf-8")
    assert "ONELAP_USERNAME=newuser" in content
    assert "ONELAP_PASSWORD=newpass" in content
    assert "STRAVA_CLIENT_ID=abc" in content
    assert "old" not in content


def test_run_onelap_auth_init_raises_on_empty_username(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda _: "  ")

    env_file = tmp_path / ".env"
    with pytest.raises(ValueError, match="username cannot be empty"):
        run_onelap_auth_init(env_file)


def test_run_onelap_auth_init_raises_on_empty_password(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda _: "user")
    monkeypatch.setattr("getpass.getpass", lambda _: "")

    env_file = tmp_path / ".env"
    with pytest.raises(ValueError, match="password cannot be empty"):
        run_onelap_auth_init(env_file)


def test_run_onelap_auth_init_prints_confirmation(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "user")
    monkeypatch.setattr("getpass.getpass", lambda _: "pass")

    env_file = tmp_path / ".env"
    run_onelap_auth_init(env_file)

    out = capsys.readouterr().out
    assert "OneLap credentials saved to .env" in out


def test_cli_runs_onelap_auth_init_and_exits_zero(monkeypatch):
    called = {"ok": False}

    def fake_run_onelap_auth_init(env_file):
        called["ok"] = True

    import run_sync

    monkeypatch.setattr(run_sync, "run_onelap_auth_init", fake_run_onelap_auth_init)

    code = run_sync.run_cli(["--onelap-auth-init"])
    assert code == 0
    assert called["ok"]
