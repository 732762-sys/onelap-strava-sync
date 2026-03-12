# OneLap same-activity multi-FIT dedupe design

Date: 2026-03-12
Status: approved

## Context

Current sync logic treats `activity_id` as the primary key for OneLap FIT downloads. In real data, OneLap can return multiple FIT files under the same `activity_id` for a day. This causes collisions in local naming and repeated Strava duplicate failures (`failed=2`) instead of correctly classifying one item as already synced.

## Goals

- Support multiple FIT files for the same `activity_id` without overwrite or drop.
- Define a file-level stable identity using `fileKey/fitUrl` as primary source.
- Keep sync idempotent and avoid repeated duplicate uploads.
- Reclassify Strava duplicate responses as dedupe, not failure.

## Non-goals

- No OAuth or auth flow changes.
- No API surface expansion beyond current CLI scope.
- No speculative support for non-FIT file types.

## Options considered

1. Recommended: file-level key based on `fileKey/fitUrl` (chosen)
   - Pros: matches upstream semantics, stable across same `activity_id`, readable logs.
   - Cons: requires model and dedupe key updates.
2. Keep `activity_id` and add sequence suffixes
   - Pros: smaller patch.
   - Cons: order-dependent and unstable if API ordering changes.
3. Pure content-hash identity
   - Pros: collision-proof by content.
   - Cons: identity only available after download; poorer traceability.

## Chosen design

### 1) Data model and identifiers

- Extend file-level activity representation with:
  - `record_key`: canonical unique key for the FIT entry.
  - `source_filename`: preferred download filename candidate.
- `record_key` selection priority:
  1. `fileKey`
  2. `fitUrl`
  3. `durl`
- `activity_id` remains a secondary field for observability and compatibility, not uniqueness.

### 2) OneLap listing behavior

- Preserve all list entries that have valid FIT URL information, even when `activity_id` repeats.
- Replace single-value cache (`activity_id -> fit_url`) with file-level mapping (`record_key -> fit_url`) or pass full item into download to avoid key loss.

### 3) Download naming strategy

- Filename source priority follows identifier priority (`fileKey`, then `fitUrl`, then `durl` basename).
- Normalize filenames:
  - ensure `.fit` suffix,
  - replace illegal filesystem characters,
  - trim unsafe trailing dots/spaces.
- Collision handling:
  - existing same-name + same-content hash => treat as already downloaded (idempotent),
  - existing same-name + different content => append deterministic suffix (`-2` or short hash) to avoid overwrite.

### 4) Sync dedupe and state

- Move to file-level fingerprint that includes `record_key` and file content hash (and keep `start_time` for temporal context):
  - recommended shape: `record_key|sha256|start_time`.
- This prevents same `activity_id` entries from collapsing into one sync identity.

### 5) Strava duplicate handling

- On `poll_upload` result containing duplicate error (`duplicate of ...`):
  - classify as deduped (`deduped += 1`),
  - do not count as failed,
  - mark fingerprint as synced to prevent repeated retries,
  - log parsed Strava activity id when available.
- Non-duplicate upload errors remain `failed += 1`.

### 6) Summary semantics

- `fetched`: number of file-level OneLap records returned after date filter.
- `deduped`: local state dedupe + Strava duplicate dedupe.
- `success`: newly uploaded and accepted activities.
- `failed`: genuine errors only (network/auth/non-duplicate upload issues).

## Error handling and observability

- Keep current error logging style and include both `activity_id` and `record_key` in error logs for diagnosis.
- Preserve exception safety in download/upload loops; a single record failure must not abort full run.

## Test plan

Update/add tests to validate:

1. `OneLapClient` preserves two entries with same `activity_id` but different `fitUrl/fileKey`.
2. Filename source priority and sanitization are correct.
3. Download collision policy: no overwrite, deterministic rename or idempotent skip.
4. `SyncEngine` uploads only unsynced file-level entries when same `activity_id` repeats.
5. Strava duplicate response increments `deduped`, not `failed`, and marks state synced.

## Acceptance criteria

Given OneLap returns two FIT records with the same `activity_id`, and one already exists in Strava:

- both FIT records are independently represented and downloaded,
- duplicate one is counted as deduped,
- unsynced one uploads successfully,
- summary resembles `success=1, deduped=1, failed=0` (not `failed=2`).
