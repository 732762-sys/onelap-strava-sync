from pathlib import Path

from sync_onelap_strava.sync_engine import SyncEngine


def test_sync_engine_uploads_only_unsynced_items(tmp_path):
    class FakeItem:
        def __init__(self, activity_id, start_time):
            self.activity_id = activity_id
            self.start_time = start_time

    class FakeOnelap:
        def list_fit_activities(self, since, limit):
            return [
                FakeItem("a1", "2026-03-10T08:00:00Z"),
                FakeItem("a2", "2026-03-10T09:00:00Z"),
                FakeItem("a3", "2026-03-10T10:00:00Z"),
            ]

        def download_fit(self, activity_id, output_dir):
            path = Path(output_dir) / f"{activity_id}.fit"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fit")
            return path

    class FakeState:
        def __init__(self):
            self.synced = {
                "hash-a1|2026-03-10T08:00:00Z",
                "hash-a2|2026-03-10T09:00:00Z",
            }

        def is_synced(self, fingerprint):
            return fingerprint in self.synced

        def mark_synced(self, fingerprint, strava_activity_id):
            self.synced.add(fingerprint)

    class FakeStrava:
        def __init__(self):
            self.upload_calls = 0

        def upload_fit(self, path):
            self.upload_calls += 1
            return 11

        def poll_upload(self, upload_id):
            return {"status": "ready", "error": None, "activity_id": 99}

    def fake_make_fingerprint(path, start_time):
        name = Path(path).stem
        return f"hash-{name}|{start_time}"

    engine = SyncEngine(
        onelap_client=FakeOnelap(),
        strava_client=FakeStrava(),
        state_store=FakeState(),
        make_fingerprint=fake_make_fingerprint,
        download_dir=tmp_path,
    )

    summary = engine.run_once(since_date="2026-03-07", limit=50)

    assert summary.fetched == 3
    assert summary.deduped == 2
    assert summary.success == 1
    assert summary.failed == 0
    assert engine.strava_client.upload_calls == 1
