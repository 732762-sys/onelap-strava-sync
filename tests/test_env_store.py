from pathlib import Path

from sync_onelap_strava.env_store import upsert_env_values


def test_upsert_env_values_updates_existing_and_appends_missing(tmp_path):
    env_path = Path(tmp_path) / ".env"
    env_path.write_text(
        "\n".join(
            [
                "STRAVA_CLIENT_ID=210500",
                "STRAVA_ACCESS_TOKEN=old-access",
                "ONELAP_USERNAME=user1",
            ]
        ),
        encoding="utf-8",
    )

    upsert_env_values(
        env_path,
        {
            "STRAVA_ACCESS_TOKEN": "new-access",
            "STRAVA_REFRESH_TOKEN": "new-refresh",
            "STRAVA_EXPIRES_AT": "1773255475",
        },
    )

    content = env_path.read_text(encoding="utf-8")
    assert "STRAVA_ACCESS_TOKEN=new-access" in content
    assert "STRAVA_REFRESH_TOKEN=new-refresh" in content
    assert "STRAVA_EXPIRES_AT=1773255475" in content
    assert "ONELAP_USERNAME=user1" in content
