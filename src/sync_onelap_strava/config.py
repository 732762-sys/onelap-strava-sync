from dataclasses import dataclass
from datetime import date
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    onelap_username: str | None
    onelap_password: str | None
    strava_client_id: str | None
    strava_client_secret: str | None
    strava_refresh_token: str | None
    strava_access_token: str | None
    strava_expires_at: int
    default_lookback_days: int
    cli_since: date | None


def load_settings(cli_since: date | None):
    load_dotenv()
    default_lookback_days = int(os.getenv("DEFAULT_LOOKBACK_DAYS", "3"))
    strava_expires_at = int(os.getenv("STRAVA_EXPIRES_AT", "0"))
    return Settings(
        onelap_username=os.getenv("ONELAP_USERNAME"),
        onelap_password=os.getenv("ONELAP_PASSWORD"),
        strava_client_id=os.getenv("STRAVA_CLIENT_ID"),
        strava_client_secret=os.getenv("STRAVA_CLIENT_SECRET"),
        strava_refresh_token=os.getenv("STRAVA_REFRESH_TOKEN"),
        strava_access_token=os.getenv("STRAVA_ACCESS_TOKEN"),
        strava_expires_at=strava_expires_at,
        default_lookback_days=default_lookback_days,
        cli_since=cli_since,
    )
