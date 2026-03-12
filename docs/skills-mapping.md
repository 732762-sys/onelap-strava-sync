# Skills to Root Code Mapping

## Skill Artifact

- `skills/onelap-strava-sync/SKILL.md`
- `skills/onelap-strava-sync/resources/commands.md`

## Entrypoint

- `run_sync.py`

## Runtime Modules

- `src/sync_onelap_strava/config.py`
- `src/sync_onelap_strava/onelap_client.py`
- `src/sync_onelap_strava/strava_client.py`
- `src/sync_onelap_strava/sync_engine.py`
- `src/sync_onelap_strava/state_store.py`

## Maintenance Rule

- Business logic changes must be made in root source files.
- The `skills/` directory is a distribution and discovery layer.
