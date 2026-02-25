---
phase: 04-frontend-es-module-refactor
plan: 02
subsystem: ui
tags: [es-modules, javascript, frontend, refactor, event-listeners]

# Dependency graph
requires:
  - phase: 04-01
    provides: "state.js, api.js, ui.js foundation modules used by single.js, bulk.js, main.js"
provides:
  - "frontend/js/single.js — file handling router + single-file conversion feature module"
  - "frontend/js/bulk.js — bulk conversion feature module"
  - "frontend/js/main.js — ES module entry point wiring all addEventListener calls"
  - "frontend/index.html — stripped HTML shell with no inline handlers, no style block, no script block"
affects:
  - "Phase 5 — any further frontend changes build on this clean ES module architecture"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Acyclic feature module dependency: single.js imports uploadBulk from bulk.js (not vice versa)"
    - "Live ES module binding reads: singleFileId/singleFormat/currentQuality used directly in async functions"
    - "Event delegation on #quality-opts for quality buttons (avoids binding to each button individually)"
    - "Positional query selectors for bulk toolbar buttons (querySelectorAll returns NodeList in DOM order)"

key-files:
  created:
    - "frontend/js/single.js"
    - "frontend/js/bulk.js"
    - "frontend/js/main.js"
  modified:
    - "frontend/index.html"
    - "frontend/js/state.js"

key-decisions:
  - "single.js imports uploadBulk from bulk.js directly (acyclic: single->bulk, no reverse) — handleFiles routing stays clean without registration pattern"
  - "setSingleFormat() added to state.js to allow selectSingleFormat to update only the format field without resetting file_id/category/fmts"
  - "ES module live bindings used for singleFileId/singleFormat/currentQuality in convertSingle() — always reflects current state.js value, no getter needed"
  - "App verified running on port 8070 (not 8071 as in plan template) — docker-compose port confirmed via docker compose ps"

patterns-established:
  - "Feature modules import from foundation modules (state/api/ui) only — no inter-feature imports except single->bulk for handleFiles routing"
  - "main.js as thin wire layer: all event binding in one file, no business logic"

requirements-completed: [UIPX-04]

# Metrics
duration: ~8min
completed: 2026-02-25
---

# Phase 4 Plan 02: Feature Modules and Entry Point Summary

**ES module refactor complete — single.js, bulk.js, main.js wire all 14 event handlers via addEventListener; index.html stripped to clean HTML shell with external CSS/JS only**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-25T03:24:16Z
- **Completed:** 2026-02-25T03:32:10Z (checkpoint reached — awaiting human verification)
- **Tasks:** 2 of 3 complete (Task 3 is human-verify checkpoint)
- **Files modified:** 5

## Accomplishments
- Created `frontend/js/single.js` with 8 exports: `uploadSingle`, `selectSingleFormat`, `convertSingle`, `resetAll`, `handleFiles`, `onFilePick`, `onDragOver`, `onDrop` — registers `selectSingleFormat` with ui.js via registration pattern
- Created `frontend/js/bulk.js` with 3 exports: `uploadBulk`, `applyGlobalFormat`, `convertBulk` — reads live state via `getBulkFiles()` getter
- Created `frontend/js/main.js` (47 lines) wiring all addEventListener calls for nav, quality, drop zone, file input, single clear/convert, bulk toolbar (apply/add/clear), bulk convert, history clear
- Stripped `frontend/index.html` to clean HTML shell: removed 487-line `<style>` block, 10 inline event handler attributes, 561-line `<script>` block; added CSS link and module script tag
- Added `setSingleFormat()` to `state.js` (Rule 2 auto-fix: needed setter for single format field)
- Docker build succeeded; all 7 modules (main.js, single.js, bulk.js, state.js, api.js, ui.js, app.css) verified serving with 200 status at http://localhost:8070

## Task Commits

Each task was committed atomically:

1. **Task 1: Create single.js and bulk.js feature modules** - `9cfe410` (feat)
2. **Task 2: Create main.js entry point and strip index.html** - `8706dcb` (feat)
3. **Task 3: Verify all features work in browser** - PENDING (human-verify checkpoint)

## Files Created/Modified
- `frontend/js/single.js` - Single-file conversion + file routing module
- `frontend/js/bulk.js` - Bulk conversion module
- `frontend/js/main.js` - ES module entry point, all addEventListener wiring
- `frontend/index.html` - Stripped to HTML shell with external CSS link and module script tag
- `frontend/js/state.js` - Added setSingleFormat() setter function

## Decisions Made
- `single.js` imports `uploadBulk` from `bulk.js` directly — the dependency is acyclic (bulk.js does not import from single.js), so no registration pattern needed for this direction.
- `setSingleFormat()` added to `state.js` — `selectSingleFormat` only needs to change the target format, not reset the entire single-file state. Adding a focused setter is cleaner than calling `setSingleFile` with all 4 args.
- ES module live bindings used directly in `convertSingle()` — `import { singleFileId, singleFormat, currentQuality }` from state.js gives live references that always reflect the current exported value, no getter wrapper needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added setSingleFormat() to state.js**
- **Found during:** Task 1 (creating single.js)
- **Issue:** `selectSingleFormat` in single.js needs to update only `singleFormat` in state. The only existing setter `setSingleFile(id, fmt, cat, fmts)` resets all 4 fields — calling it would wipe `singleFileId` which is needed for conversion.
- **Fix:** Added `setSingleFormat(fmt)` to `state.js` that updates only the `singleFormat` variable.
- **Files modified:** `frontend/js/state.js`
- **Verification:** `node --check` passes; function is used correctly in selectSingleFormat
- **Committed in:** `9cfe410` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical setter)
**Impact on plan:** Essential for correct format selection behavior. No scope creep.

## Issues Encountered
- App runs on port 8070, not 8071 as noted in plan's checkpoint action. Verified via `docker compose ps`. All module URLs confirmed serving at http://localhost:8070.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Phase 4 refactor complete pending human browser verification (Task 3)
- All 6 JS modules serve with 200 status; ES module dependency graph is acyclic
- Phase 5 can proceed after human verification confirms all features work in browser

---
*Phase: 04-frontend-es-module-refactor*
*Completed: 2026-02-25 (checkpoint — human verify pending)*
