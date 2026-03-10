from datetime import date

from sync_onelap_strava.config import load_settings


def test_default_lookback_days_is_3(monkeypatch):
    monkeypatch.delenv("DEFAULT_LOOKBACK_DAYS", raising=False)
    s = load_settings(cli_since=None)
    assert s.default_lookback_days == 3


def test_load_settings_reads_env_and_cli_since(monkeypatch):
    monkeypatch.setenv("ONELAP_USERNAME", "u")
    monkeypatch.setenv("ONELAP_PASSWORD", "p")
    monkeypatch.setenv("STRAVA_CLIENT_ID", "id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "r")
    monkeypatch.setenv("STRAVA_ACCESS_TOKEN", "a")
    monkeypatch.setenv("STRAVA_EXPIRES_AT", "123")
    monkeypatch.setenv("DEFAULT_LOOKBACK_DAYS", "5")

    s = load_settings(cli_since=date(2026, 3, 1))
    assert s.default_lookback_days == 5
    assert s.onelap_username == "u"
    assert s.strava_client_id == "id"
