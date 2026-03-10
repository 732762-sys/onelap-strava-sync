# OneLap Adapter Notes

`OneLapClient` now uses direct OneLap HTTP APIs (no placeholder backend):

- `login()` -> POST `https://www.onelap.cn/login` and stores session cookie
- `list_fit_activities(since, limit)` -> GET `https://www.onelap.cn/api/activities`, normalizes to `OneLapActivity`, applies since-date filter, caches `fit_url`
- `download_fit(activity_id, output_dir)` -> downloads cached `fit_url` to `<output_dir>/<activity_id>.fit`

Runtime behavior notes:

- On first list request, 401 triggers one login attempt and retry.
- `SyncEngine` remains responsible for dedupe/state transitions and Strava upload flow.
