import responses
import pytest

from sync_onelap_strava.strava_client import StravaClient
from sync_onelap_strava.strava_oauth_init import (
    build_authorize_url,
    ensure_required_scope,
    exchange_code_for_tokens,
)


@responses.activate
def test_refresh_token_called_when_access_token_expired(tmp_path):
    responses.add(
        responses.POST,
        "https://www.strava.com/oauth/token",
        json={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_at": 9999999999,
        },
        status=200,
    )
    client = StravaClient(
        client_id="id",
        client_secret="secret",
        refresh_token="old",
        access_token="expired",
        expires_at=0,
    )
    token = client.ensure_access_token()
    assert token == "new-token"


def test_build_authorize_url_includes_force_and_activity_write():
    url = build_authorize_url(
        client_id="210500", redirect_uri="http://localhost:8765/callback"
    )
    assert "approval_prompt=force" in url
    assert "scope=read%2Cactivity%3Awrite" in url
    assert "client_id=210500" in url


@responses.activate
def test_exchange_code_for_tokens_returns_required_fields():
    responses.add(
        responses.POST,
        "https://www.strava.com/oauth/token",
        json={
            "access_token": "a1",
            "refresh_token": "r1",
            "expires_at": 1773255475,
        },
        status=200,
    )

    payload = exchange_code_for_tokens(
        client_id="210500",
        client_secret="secret",
        code="abc",
    )

    assert payload["access_token"] == "a1"
    assert payload["refresh_token"] == "r1"
    assert payload["expires_at"] == 1773255475


def test_ensure_required_scope_accepts_activity_write():
    ensure_required_scope("read,activity:write")


def test_ensure_required_scope_raises_without_activity_write():
    with pytest.raises(ValueError):
        ensure_required_scope("read")


@responses.activate
def test_refresh_token_persists_updated_values(monkeypatch):
    saved = {}

    def fake_save(_path, values):
        saved.update(values)

    monkeypatch.setattr("sync_onelap_strava.strava_client.upsert_env_values", fake_save)

    responses.add(
        responses.POST,
        "https://www.strava.com/oauth/token",
        json={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_at": 1773255475,
        },
        status=200,
    )

    client = StravaClient(
        client_id="id",
        client_secret="secret",
        refresh_token="old-refresh",
        access_token="expired",
        expires_at=0,
    )

    token = client.ensure_access_token()
    assert token == "new-token"
    assert saved["STRAVA_ACCESS_TOKEN"] == "new-token"
    assert saved["STRAVA_REFRESH_TOKEN"] == "new-refresh"
    assert saved["STRAVA_EXPIRES_AT"] == "1773255475"
