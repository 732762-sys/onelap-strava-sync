from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests


@dataclass
class OneLapActivity:
    activity_id: str
    start_time: str


class OneLapClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self):
        response = self.session.post(
            f"{self.base_url}/login",
            data={"username": self.username, "password": self.password},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError("OneLap login failed")
        return True

    def list_fit_activities(self, since: date, limit: int):
        raise NotImplementedError

    def download_fit(self, activity_id: str, output_dir: Path):
        raise NotImplementedError
