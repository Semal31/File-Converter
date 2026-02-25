---
phase: 05-progress-wiring-and-ui-polish
plan: 04
subsystem: ui
tags: [bulk, progress, sse, xhr, per-file, download-zip, smart-defaults, remove-button]

# Dependency graph
requires:
  - phase: 05-progress-wiring-and-ui-polish
    plan: 01
    provides: CSS design tokens and bulk-file-row base styles
  - phase: 05-progress-wiring-and-ui-polish
    plan: 02
    provides: apiBulkUploadWithProgress, apiConvert, watchJobProgress, apiBulkDownloadZip in api.js
  - phase: 05-progress-wiring-and-ui-polish
    plan: 03
    provides: updateBulkRowStatus pattern for bulk row state management
provides:
  - Per-file progress bars in each bulk row (upload and SSE conversion phase)
  - X remove button on pending bulk rows — removes file before conversion starts
  - Individual Download button per row after conversion completes
  - Smart format defaults — each row pre-fills first available format on upload
  - Summary banner showing success/partial/failure counts after batch completes
  - Download All as ZIP button calling apiBulkDownloadZip with all completed download_ids
  - removeBulkFile(index) mutation in state.js
  - updateBulkRowProgress, updateBulkRowAction exported from ui.js
affects: [05-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - per-file-apiConvert-not-apiBulkConvert
    - Promise.allSettled-for-parallel-SSE
    - event-delegation-for-dynamic-bulk-rows
    - smart-format-default-first-available

key-files:
  created: []
  modified:
    - frontend/js/state.js
    - frontend/js/ui.js
    - frontend/js/bulk.js
    - frontend/js/single.js
    - frontend/css/app.css
    - frontend/index.html

key-decisions:
  - "Per-file apiConvert (not apiBulkConvert) — gives one job_id per file for independent SSE tracking"
  - "Promise.allSettled opens all SSE connections simultaneously — rows update independently"
  - "Smart default: renderBulkRow sets f.target_format = f.available_formats[0] if none set"
  - "X remove button only shown on pending rows — hidden once converting starts"
  - "updateBulkRowAction called from updateBulkRowStatus — action cell and select state always in sync"
  - "resetAll() extended with bulk-summary and bulk-download-all cleanup so repeat uploads start clean"

patterns-established:
  - "bulk row IDs are namespaced: bulk-fill-{i}, bulk-plabel-{i}, bulk-status-{i}, bulk-action-{i}"
  - "updateBulkRowStatus always calls updateBulkRowAction to keep action cell in sync with status"
  - "initBulkListDelegation handles both SELECT change and .bulk-row-remove click via delegation"

requirements-completed: [UIPX-03, PROG-02, PROG-03]

# Metrics
duration: ~2min
completed: 2026-02-25
---

# Phase 5 Plan 04: Bulk Workflow Overhaul Summary

**Per-file XHR upload + independent SSE conversion tracking per bulk row, with X remove buttons, per-row Download buttons, smart format defaults, summary banner, and Download All as ZIP button**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-25T15:53:28Z
- **Completed:** 2026-02-25T15:56:24Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Replaced monolithic `apiBulkConvert` with per-file `apiConvert` calls — each file gets its own `job_id` for independent SSE tracking
- All SSE connections open simultaneously via `Promise.allSettled` — each row's progress bar updates independently without blocking others
- Smart format defaults: `renderBulkRow` sets `f.target_format = f.available_formats[0]` if none set, so all rows start pre-filled
- X remove button on pending rows deletes a file from the batch before conversion; `initBulkListDelegation` handles clicks via event delegation
- Per-row Download button (`<a class="bulk-row-dl">`) appears on completed rows; `updateBulkRowAction` keeps it in sync with status transitions
- Summary banner shows all-success/partial/all-failed states; Download All ZIP button triggers `apiBulkDownloadZip(downloadIds)` for a single ZIP

## Task Commits

Each task was committed atomically:

1. **Task 1: Update state, UI rendering, CSS, and HTML** - `645da97` (feat)
2. **Task 2: Rewrite bulk.js for per-file XHR uploads with per-row SSE tracking** - `c86f498` (feat)

## Files Created/Modified

- `frontend/js/state.js` - Added `removeBulkFile(index)` mutation; updated schema comment with `download_id`/`progress` fields
- `frontend/js/ui.js` - Rewrote `renderBulkRow` with progress bar/X button/download button/smart default; added `updateBulkRowProgress`, `updateBulkRowAction`; updated `updateBulkRowStatus` to call `updateBulkRowAction`; updated `initBulkListDelegation` with remove button delegation; added `removeBulkFile`/`getBulkFiles`/`apiDownloadUrl` imports
- `frontend/js/bulk.js` - Complete rewrite: `uploadBulk` uses `apiBulkUploadWithProgress`; `convertBulk` calls `apiConvert` per file then `watchJobProgress` per job; summary banner; Download All ZIP; removed `apiBulkConvert` dependency
- `frontend/js/single.js` - Extended `resetAll()` to hide/clear `#bulk-summary` and `#bulk-download-all`
- `frontend/css/app.css` - Added styles for `.bulk-file-progress`/`.bulk-progress-bar`/`.bulk-progress-fill`, `.bulk-row-remove`, `.bulk-row-dl`, `.bulk-file-action`, `.bulk-summary` with success/partial/failure variants
- `frontend/index.html` - Added `#bulk-summary` and `#bulk-download-all` divs after the bulk Convert All button

## Decisions Made

- **apiConvert per file:** Using the single-file `/api/convert` endpoint for each bulk item gives one `job_id` per file, enabling independent SSE tracking. The old `apiBulkConvert` returned a batch result without per-file progress handles.
- **Promise.allSettled for SSE:** All `watchJobProgress` promises run concurrently — no sequential waiting. `allSettled` (not `all`) ensures all rows reach a terminal state even if some fail.
- **Smart default in renderBulkRow:** Pre-filling `f.target_format` on render means the Convert All button is immediately usable after upload without requiring user format selection on every row.
- **updateBulkRowAction called from updateBulkRowStatus:** Keeps action cell synchronized with row status transitions automatically — no caller needs to manage action cell separately.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Bulk workflow overhaul complete — all three requirements (UIPX-03, PROG-02, PROG-03) fulfilled
- Phase 5 Plan 05 can proceed (final polish / remaining items)
- No blockers

## Self-Check: PASSED

- frontend/js/state.js: FOUND (removeBulkFile exported)
- frontend/js/ui.js: FOUND (updateBulkRowProgress + updateBulkRowAction exported)
- frontend/js/bulk.js: FOUND (apiConvert + watchJobProgress + Promise.allSettled + apiBulkDownloadZip)
- frontend/css/app.css: FOUND (bulk-progress-fill + bulk-row-remove + bulk-row-dl + bulk-summary)
- frontend/index.html: FOUND (bulk-summary + bulk-download-all)
- 05-04-SUMMARY.md: FOUND
- Commit 645da97 (Task 1): FOUND
- Commit c86f498 (Task 2): FOUND
- apiBulkConvert absent from bulk.js: CONFIRMED

---
*Phase: 05-progress-wiring-and-ui-polish*
*Completed: 2026-02-25*
