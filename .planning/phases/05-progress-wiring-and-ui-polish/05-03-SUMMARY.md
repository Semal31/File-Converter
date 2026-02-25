---
phase: 05-progress-wiring-and-ui-polish
plan: 03
subsystem: single-file-progress
tags: [progress, xhr, sse, two-phase-bar, single-file, download-button]

# Dependency graph
requires:
  - phase: 05-progress-wiring-and-ui-polish
    plan: 01
    provides: CSS progress-bar-fill styling with transition
  - phase: 05-progress-wiring-and-ui-polish
    plan: 02
    provides: apiUploadWithProgress, watchJobProgress in api.js
provides:
  - Two-phase XHR upload + SSE conversion progress bar for single-file flow
  - setProgressBar and showDownloadButton helper functions in ui.js
  - Download button (no auto-download) shown on conversion completion
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [two-phase-progress-bar, XHR-upload-0-50, SSE-convert-50-100, download-button-no-auto-dl]

key-files:
  created: []
  modified:
    - frontend/js/ui.js
    - frontend/js/single.js
    - frontend/index.html

key-decisions:
  - "Upload phase maps XHR ratio (0-1) to bar (0-50%); conversion phase maps SSE percent (0-99) to bar (50-100%)"
  - "Output filename derived from original name + target format (not backend output_filename which is absent in Phase 3 contract)"
  - "Download button shown on completion, no auto-download per user decision locked in planning"
  - "resetAll() extended to also clear download-area-single so repeat uploads start clean"

# Metrics
duration: ~1 min
completed: 2026-02-25
tasks: 2
files_modified: 3
---

# Phase 5 Plan 03: Single-File Two-Phase Progress Bar Summary

Two-phase XHR upload (0-50%) + SSE conversion (50-100%) progress bar wired into single.js, with setProgressBar/showDownloadButton helpers added to ui.js and HTML updated with labelled progress and download area.

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-25T15:49:46Z
- **Completed:** 2026-02-25T15:50:53Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `setProgressBar(fillId, labelId, percent, labelText)` to ui.js — sets fill width and label text atomically, clamped 0-100
- Added `showDownloadButton(containerId, downloadId, filename)` to ui.js — XSS-safe download link using existing `esc()` helper
- Updated index.html progress section: added `id="progress-label-single"` for dynamic updates and `#download-area-single` container
- Rewrote `uploadSingle()` in single.js to use `apiUploadWithProgress` with XHR progress callback (0-50% bar range)
- Rewrote `convertSingle()` in single.js to use `apiConvert` + `watchJobProgress` SSE stream (50-100% bar range)
- Download button shown at completion — no auto-download (per user decision)
- History records `download_id` from SSE done event resolution
- `resetAll()` updated to also reset `#download-area-single`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add progress UI helpers to ui.js and update HTML progress section** - `5e04fe0` (feat)
2. **Task 2: Rewrite single.js for two-phase progress (XHR upload + SSE convert)** - `31ba381` (feat)

## Files Created/Modified

- `frontend/js/ui.js` - Added `setProgressBar` and `showDownloadButton` exported functions
- `frontend/js/single.js` - Rewrote `uploadSingle` (XHR progress) and `convertSingle` (SSE progress + download button); updated `resetAll`
- `frontend/index.html` - Added `id="progress-label-single"` to progress label; added `#download-area-single` container

## Decisions Made

- **Two-phase bar mapping:** Upload ratio (0.0-1.0) maps to bar 0-50%; SSE percent (0-99) maps to bar 50-99.5%; done event sets 100%
- **Filename derivation:** `stem = originalName.replace(/\.[^.]+$/, '')` + `.${singleFormat}` — backend Phase 3 contract returns only `{job_id}` from `/api/convert`, not `output_filename`
- **No progress bar reset in `finally`:** On success, 100% bar + Download button stay visible; bar only hides on error path
- **resetAll extension:** download-area-single cleared in `resetAll()` so uploading a new file starts with a clean slate

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- frontend/js/ui.js: FOUND (setProgressBar + showDownloadButton exported)
- frontend/js/single.js: FOUND (apiUploadWithProgress + watchJobProgress used)
- frontend/index.html: FOUND (progress-label-single + download-area-single present)
- 05-03-SUMMARY.md: FOUND
- Commit 5e04fe0 (Task 1): FOUND
- Commit 31ba381 (Task 2): FOUND
- No old data.download_id references in convertSingle: CLEAN
- No old data.output_filename references in convertSingle: CLEAN
- No old apiUpload( calls remaining: CLEAN

---
*Phase: 05-progress-wiring-and-ui-polish*
*Completed: 2026-02-25*
