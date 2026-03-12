from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
from pathlib import Path
import re
from urllib.parse import urlparse
from uuid import uuid4

import requests


@dataclass
class OneLapActivity:
    activity_id: str
    start_time: str
    fit_url: str
    record_key: str
    source_filename: str


class OneLapClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._activity_fit_urls: dict[str, tuple[str, str]] = {}

    def login(self):
        request_data = {
            "account": self.username,
            "password": hashlib.md5(self.password.encode("utf-8")).hexdigest(),
        }
        response = self.session.post(
            f"{self.base_url}/api/login",
            data=request_data,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") not in {0, 200}:
            raise RuntimeError(
                f"OneLap login failed: {payload.get('error', 'unknown')}"
            )
        return True

    def list_fit_activities(self, since: date, limit: int):
        payload = self._fetch_activities_payload()
        items = payload.get("data", [])
        cutoff = since.isoformat()
        result: list[OneLapActivity] = []

        for raw in items:
            activity_id = str(raw.get("id") or raw.get("activity_id") or "")
            start_time = self._parse_start_time(raw)
            fit_url = str(
                raw.get("fit_url") or raw.get("fitUrl") or raw.get("durl") or ""
            ).strip()
            record_key, source_filename = self._build_record_identity(raw)
            if not activity_id or not start_time or not fit_url:
                continue
            if start_time[:10] < cutoff:
                continue
            if not record_key:
                continue

            normalized = OneLapActivity(
                activity_id=activity_id,
                start_time=start_time,
                fit_url=fit_url,
                record_key=record_key,
                source_filename=source_filename,
            )
            self._activity_fit_urls[record_key] = (fit_url, source_filename)
            result.append(normalized)
            if len(result) >= limit:
                break

        return result

    def _fetch_activities_payload(self) -> dict:
        for attempt in range(2):
            response = self.session.get("http://u.onelap.cn/analysis/list", timeout=30)
            if self._requires_login(response):
                if attempt == 1:
                    raise RuntimeError("OneLap activities request requires login")
                self.login()
                continue

            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError:
                if attempt == 1:
                    raise RuntimeError("OneLap activities response is not JSON")
                self.login()
                continue

            if isinstance(payload, dict):
                return payload
            if attempt == 1:
                raise RuntimeError("OneLap activities payload is invalid")
            self.login()

        raise RuntimeError("failed to fetch OneLap activities")

    def _requires_login(self, response: requests.Response) -> bool:
        if response.status_code in {401, 403}:
            return True

        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" in content_type:
            return True

        return "login.html" in response.url

    def _parse_start_time(self, raw: dict) -> str:
        value = raw.get("start_time")
        if value:
            return str(value)

        created_at = raw.get("created_at")
        if isinstance(created_at, int):
            return datetime.fromtimestamp(created_at, UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        if isinstance(created_at, str):
            if created_at.isdigit():
                return datetime.fromtimestamp(int(created_at), UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            return created_at
        return ""

    def _build_record_identity(self, raw: dict) -> tuple[str, str]:
        file_key = str(raw.get("fileKey") or "").strip()
        if file_key:
            return f"fileKey:{file_key}", file_key

        fit_url = str(raw.get("fit_url") or raw.get("fitUrl") or "").strip()
        if fit_url:
            return f"fitUrl:{fit_url}", fit_url

        durl = str(raw.get("durl") or "").strip()
        if durl:
            return f"durl:{durl}", durl

        return "", ""

    def _normalize_fit_filename(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            text = "activity.fit"

        parsed = urlparse(text)
        path_source = parsed.path if parsed.path else text
        filename = Path(path_source.replace("\\", "/")).name
        filename = re.sub(r'[<>:"/\\|?*]+', "_", filename).strip().strip(". ")
        if not filename:
            filename = "activity"
        if not filename.lower().endswith(".fit"):
            filename = f"{filename}.fit"
        return filename

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                if chunk:
                    digest.update(chunk)
        return digest.hexdigest()

    def _select_output_path(self, target: Path, downloaded_path: Path) -> Path:
        if not target.exists():
            return target

        downloaded_hash = self._hash_file(downloaded_path)
        if self._hash_file(target) == downloaded_hash:
            downloaded_path.unlink(missing_ok=True)
            return target

        stem = target.stem
        suffix = target.suffix
        index = 2
        while True:
            candidate = target.with_name(f"{stem}-{index}{suffix}")
            if not candidate.exists():
                return candidate
            if self._hash_file(candidate) == downloaded_hash:
                downloaded_path.unlink(missing_ok=True)
                return candidate
            index += 1

    def download_fit(self, record_key: str, output_dir: Path):
        fit_meta = self._activity_fit_urls.get(record_key)
        if fit_meta is None:
            raise RuntimeError(f"missing fit_url for record {record_key}")
        fit_url, source_filename = fit_meta

        if fit_url.startswith("http://") or fit_url.startswith("https://"):
            download_url = fit_url
        else:
            download_url = f"{self.base_url}/{fit_url.lstrip('/')}"

        response = self.session.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        safe_name = self._normalize_fit_filename(source_filename)
        target_path = Path(output_dir) / safe_name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = target_path.with_name(f".{target_path.name}.{uuid4().hex}.tmp")
        with temp_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

        output_path = self._select_output_path(target_path, temp_path)
        if temp_path.exists():
            temp_path.replace(output_path)
        return output_path
