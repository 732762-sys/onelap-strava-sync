from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests


@dataclass
class OneLapActivity:
    activity_id: str
    start_time: str
    fit_url: str


class OneLapClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._activity_fit_urls: dict[str, str] = {}

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
        response = self.session.get(f"{self.base_url}/api/activities", timeout=30)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        cutoff = since.isoformat()
        result: list[OneLapActivity] = []

        for raw in items:
            activity_id = str(raw.get("id") or raw.get("activity_id") or "")
            start_time = str(raw.get("start_time") or "")
            fit_url = str(raw.get("fit_url") or "")
            if not activity_id or not start_time or not fit_url:
                continue
            if start_time[:10] < cutoff:
                continue

            normalized = OneLapActivity(
                activity_id=activity_id,
                start_time=start_time,
                fit_url=fit_url,
            )
            self._activity_fit_urls[activity_id] = fit_url
            result.append(normalized)
            if len(result) >= limit:
                break

        return result

    def download_fit(self, activity_id: str, output_dir: Path):
        raise NotImplementedError
