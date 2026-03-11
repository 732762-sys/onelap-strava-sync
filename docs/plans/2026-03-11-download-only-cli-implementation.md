# Download-Only CLI Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `--download-only` mode to `run_sync.py` so users can download FIT files from OneLap without uploading to Strava.

**Architecture:** Keep existing sync flow untouched for default mode. Add a CLI branch for download-only in `run_sync.py` that validates only OneLap settings, lists activities, downloads FIT files, prints one line per file with timestamp and filename, and prints a final summary. Avoid writing upload state in download-only mode.

**Tech Stack:** Python 3.11+, `argparse`, existing OneLap adapter (`requests`), `pytest`.

---

### Task 1: Add CLI Surface for Download-Only Flag

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `run_sync.py`

**Step 1: Write the failing test**

In `tests/test_cli.py`, add:

```python
def test_cli_accepts_download_only_argument_and_runs_engine(capsys):
    class FakeEngine:
        def run_once(self, since_date=None, limit=50):
            return SyncSummary(fetched=0, deduped=0, success=0, failed=0)

    from run_sync import run_cli

    exit_code = run_cli(["--download-only"], engine=FakeEngine())
    assert exit_code == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_cli_accepts_download_only_argument_and_runs_engine -v`
Expected: FAIL (`unrecognized arguments: --download-only`).

**Step 3: Write minimal implementation**

In `run_sync.py`:

- Add parser flag:

```python
parser.add_argument(
    "--download-only",
    action="store_true",
    help="Download FIT files from OneLap without uploading to Strava",
)
```

- For now, keep behavior same when `engine` is injected (this test only ensures CLI accepts the flag).

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add run_sync.py tests/test_cli.py
git commit -m "feat: add download-only cli flag"
```

### Task 2: Implement Download-Only Runtime Path (No Strava Requirement)

**Files:**
- Create: `tests/test_cli_download_only.py`
- Modify: `run_sync.py`

**Step 1: Write the failing test**

Create `tests/test_cli_download_only.py` with:

```python
def test_download_only_mode_does_not_require_strava_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELAP_USERNAME", "u")
    monkeypatch.setenv("ONELAP_PASSWORD", "p")
    monkeypatch.delenv("STRAVA_CLIENT_ID", raising=False)
    monkeypatch.delenv("STRAVA_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("STRAVA_REFRESH_TOKEN", raising=False)

    class FakeOneLapClient:
        def list_fit_activities(self, since, limit):
            class Item:
                activity_id = "a1"
                start_time = "2026-03-09T08:00:00Z"

            return [Item()]

        def download_fit(self, activity_id, output_dir):
            p = tmp_path / f"{activity_id}.fit"
            p.write_bytes(b"fit")
            return p

    import run_sync

    monkeypatch.setattr(
        run_sync,
        "OneLapClient",
        lambda base_url, username, password: FakeOneLapClient(),
    )

    code = run_sync.run_cli(["--download-only", "--since", "2026-03-01"])
    assert code == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_download_only.py::test_download_only_mode_does_not_require_strava_settings -v`
Expected: FAIL (still validating Strava settings via default engine path).

**Step 3: Write minimal implementation**

In `run_sync.py`:

- Add helper to validate OneLap-only settings:

```python
def _validate_onelap_settings(settings):
    required = {
        "ONELAP_USERNAME": settings.onelap_username,
        "ONELAP_PASSWORD": settings.onelap_password,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"missing required settings: {', '.join(missing)}")
```

- Add helper function:

```python
def run_download_only(since_value):
    settings = load_settings(cli_since=since_value)
    _validate_onelap_settings(settings)
    onelap = OneLapClient(
        base_url="https://www.onelap.cn",
        username=settings.onelap_username or "",
        password=settings.onelap_password or "",
    )
    effective_since = since_value
    if effective_since is None:
        from datetime import timedelta

        effective_since = date.today() - timedelta(days=settings.default_lookback_days)

    items = onelap.list_fit_activities(since=effective_since, limit=50)
    fetched = len(items)
    downloaded = 0
    failed = 0
    for item in items:
        try:
            onelap.download_fit(item.activity_id, Path("downloads"))
            downloaded += 1
        except Exception:
            failed += 1
    print(f"download-only fetched {fetched} -> downloaded {downloaded} -> failed {failed}")
    return 0
```

- In `run_cli`, branch before building default engine:

```python
if args.download_only and engine is None:
    return run_download_only(since_value)
```

Keep default path unchanged for non-download-only mode.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_cli_download_only.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add run_sync.py tests/test_cli_download_only.py
git commit -m "feat: add download-only execution path without strava requirements"
```

### Task 3: Add Per-FIT Line Output (Time + Filename)

**Files:**
- Modify: `tests/test_cli_download_only.py`
- Modify: `run_sync.py`

**Step 1: Write the failing test**

Add test in `tests/test_cli_download_only.py`:

```python
def test_download_only_prints_one_line_per_fit_with_time_and_filename(monkeypatch, capsys):
    monkeypatch.setenv("ONELAP_USERNAME", "u")
    monkeypatch.setenv("ONELAP_PASSWORD", "p")

    class Item:
        def __init__(self, activity_id, start_time):
            self.activity_id = activity_id
            self.start_time = start_time

    class FakeOneLapClient:
        def list_fit_activities(self, since, limit):
            return [
                Item("a1", "2026-03-08T08:00:00Z"),
                Item("a2", "2026-03-09T08:00:00Z"),
            ]

        def download_fit(self, activity_id, output_dir):
            p = Path(output_dir) / f"{activity_id}.fit"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"fit")
            return p

    import run_sync

    monkeypatch.setattr(
        run_sync,
        "OneLapClient",
        lambda base_url, username, password: FakeOneLapClient(),
    )

    code = run_sync.run_cli(["--download-only", "--since", "2026-03-01"])
    out = capsys.readouterr().out

    assert code == 0
    assert "2026-03-08T08:00:00Z  a1.fit" in out
    assert "2026-03-09T08:00:00Z  a2.fit" in out
    assert "download-only fetched 2 -> downloaded 2 -> failed 0" in out
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_download_only.py::test_download_only_prints_one_line_per_fit_with_time_and_filename -v`
Expected: FAIL (missing per-item line output).

**Step 3: Write minimal implementation**

In `run_download_only`, update loop to print per item:

```python
for item in items:
    filename = f"{item.activity_id}.fit"
    try:
        onelap.download_fit(item.activity_id, Path("downloads"))
        print(f"{item.start_time}  {filename}")
        downloaded += 1
    except Exception as exc:
        print(f"{item.start_time}  {filename}  FAILED: {exc}")
        failed += 1
```

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_cli_download_only.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add run_sync.py tests/test_cli_download_only.py
git commit -m "feat: print per-fit download lines in download-only mode"
```

### Task 4: Add Failure-Line and Exit-Code Coverage

**Files:**
- Modify: `tests/test_cli_download_only.py`

**Step 1: Write the failing tests**

Add tests:

```python
def test_download_only_prints_failed_line_for_item_errors(monkeypatch, capsys):
    monkeypatch.setenv("ONELAP_USERNAME", "u")
    monkeypatch.setenv("ONELAP_PASSWORD", "p")

    class Item:
        def __init__(self, activity_id, start_time):
            self.activity_id = activity_id
            self.start_time = start_time

    class FakeOneLapClient:
        def list_fit_activities(self, since, limit):
            return [Item("a1", "2026-03-08T08:00:00Z")]

        def download_fit(self, activity_id, output_dir):
            raise RuntimeError("disk full")

    import run_sync

    monkeypatch.setattr(
        run_sync,
        "OneLapClient",
        lambda base_url, username, password: FakeOneLapClient(),
    )

    code = run_sync.run_cli(["--download-only", "--since", "2026-03-01"])
    out = capsys.readouterr().out

    assert code == 0
    assert "2026-03-08T08:00:00Z  a1.fit  FAILED: disk full" in out
    assert "download-only fetched 1 -> downloaded 0 -> failed 1" in out


def test_download_only_returns_nonzero_when_onelap_settings_missing(monkeypatch):
    monkeypatch.delenv("ONELAP_USERNAME", raising=False)
    monkeypatch.delenv("ONELAP_PASSWORD", raising=False)

    from run_sync import run_cli

    code = run_cli(["--download-only"])
    assert code != 0
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli_download_only.py -v`
Expected: FAIL initially if behavior mismatches exact lines or missing fatal handling.

**Step 3: Write minimal implementation**

- Ensure failure lines include exact `FAILED: <error>` text.
- Reuse existing top-level fatal handling in `run_cli` so missing OneLap settings returns non-zero.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_cli_download_only.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add run_sync.py tests/test_cli_download_only.py
git commit -m "test: cover download-only failure lines and missing settings"
```

### Task 5: Update User Documentation for Download-Only Mode

**Files:**
- Modify: `README.md`

**Step 1: Write the failing doc test**

In `tests/test_e2e_dry_run.py`, add:

```python
def test_readme_documents_download_only_mode():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "--download-only" in text
    assert "download-only fetched" in text
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_e2e_dry_run.py::test_readme_documents_download_only_mode -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Update `README.md` with:

- Example command: `python run_sync.py --download-only --since 2026-03-01`
- Clarify that Strava keys are not required in this mode
- Show example output format:
  - `2026-03-09T08:00:00Z  a2.fit`
  - `download-only fetched X -> downloaded Y -> failed Z`

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_e2e_dry_run.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md tests/test_e2e_dry_run.py
git commit -m "docs: add download-only mode usage and output examples"
```

### Task 6: Final Verification

**Files:**
- No new files

**Step 1: Run full test suite**

Run: `python -m pytest -v`
Expected: PASS (all tests green).

**Step 2: Verify help output includes new flag**

Run: `python run_sync.py --help`
Expected: output includes `--download-only`.

**Step 3: Verify runtime behavior manually (without Strava env)**

Run: `python run_sync.py --download-only --since 2026-03-01`
Expected:

- no fatal error about missing Strava settings
- per-FIT lines printed as `<start_time>  <activity_id>.fit`
- final summary printed

**Step 4: Commit final touch-ups if needed**

```bash
git add <any-touched-files>
git commit -m "chore: finalize download-only cli mode verification fixes"
```
