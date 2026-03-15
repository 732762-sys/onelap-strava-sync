import getpass
from pathlib import Path

from sync_onelap_strava.env_store import upsert_env_values


def run_onelap_auth_init(env_file: Path) -> None:
    username = input("OneLap username: ").strip()
    if not username:
        raise ValueError("username cannot be empty")

    password = getpass.getpass("OneLap password: ")
    if not password:
        raise ValueError("password cannot be empty")

    upsert_env_values(
        env_file,
        {
            "ONELAP_USERNAME": username,
            "ONELAP_PASSWORD": password,
        },
    )
    print("OneLap credentials saved to .env")
