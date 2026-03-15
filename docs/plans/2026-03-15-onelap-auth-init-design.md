# OneLap Account Init Design

## Problem

OneLap credentials (username, password) must be manually edited into `.env`. This is error-prone and inconsistent with the interactive `--strava-auth-init` flow.

## Solution

Add `--onelap-auth-init` CLI flag that interactively prompts for OneLap username and password, then saves them to `.env`.

## Design

### New module: `onelap_auth_init.py`

- `run_onelap_auth_init(env_file: Path) -> None`
- Prompts username via `input()`
- Prompts password via `getpass.getpass()` (hidden input)
- Saves `ONELAP_USERNAME` and `ONELAP_PASSWORD` to `.env` via `upsert_env_values()`
- Prints confirmation message

### CLI change: `cli.py`

- Add `--onelap-auth-init` argument (store_true)
- Add branch in `run_cli()` before other mode branches
- Import and call `run_onelap_auth_init()`

### Wrapper: `run_sync.py`

- Export `run_onelap_auth_init` for test monkeypatching

### Tests: `test_onelap_auth_init.py`

- Unit test: mock `input()` and `getpass.getpass()`, verify `.env` written correctly
- CLI integration test: mock handler, verify exit code 0

### Documentation updates

- README.md: add OneLap auth init section
- commands.md: add `--onelap-auth-init` entry
- SKILL.md: add trigger for OneLap account initialization
- skills-mapping.md: add `onelap_auth_init.py` to runtime modules
- test_skill_repository_structure.py: add assertion for `--onelap-auth-init`
