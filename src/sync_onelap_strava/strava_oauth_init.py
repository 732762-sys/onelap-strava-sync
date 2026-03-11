from urllib.parse import parse_qs, urlencode, urlparse

import requests


def build_authorize_url(client_id: str, redirect_uri: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",
            "scope": "read,activity:write",
        }
    )
    return f"https://www.strava.com/oauth/authorize?{query}"


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str) -> dict:
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "expires_at": payload["expires_at"],
    }


def ensure_required_scope(scope_csv: str) -> None:
    scopes = {s.strip() for s in scope_csv.split(",") if s.strip()}
    if "activity:write" not in scopes:
        raise ValueError("missing required scope: activity:write")


def parse_callback_url(url: str) -> tuple[str, str]:
    query = parse_qs(urlparse(url).query)
    code = (query.get("code") or [""])[0]
    scope = (query.get("scope") or [""])[0]
    if not code:
        raise ValueError("missing code in callback url")
    return code, scope
