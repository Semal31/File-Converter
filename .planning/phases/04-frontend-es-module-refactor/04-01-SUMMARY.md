---
phase: 04-frontend-es-module-refactor
plan: 01
subsystem: ui
tags: [es-modules, javascript, css, frontend, refactor]

# Dependency graph
requires: []
provides:
  - "frontend/css/app.css — all CSS extracted from index.html style block (487 lines)"
  - "frontend/js/state.js — shared mutable state singleton with 7 export let vars and 9 mutation functions"
  - "frontend/js/api.js — all fetch() calls isolated as 5 named exports"
  - "frontend/js/ui.js — 18 DOM helper and rendering functions as named exports"
affects:
  - "04-02 and beyond — all subsequent phase 4 plans import from these foundation modules"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ES module export let pattern for shared mutable state with setter functions"
    - "Registration pattern (registerSelectSingleFormat) to break circular dependency between ui.js and single.js"
    - "Event delegation on #bulk-file-list instead of inline onchange handlers"

key-files:
  created:
    - "frontend/css/app.css"
    - "frontend/js/state.js"
    - "frontend/js/api.js"
    - "frontend/js/ui.js"
  modified: []

key-decisions:
  - "state.js uses export let for all state vars; mutation functions exported separately since importers cannot reassign export let bindings"
  - "setQuality() stays in state.js (not ui.js) — it is atomically coupled to the state change and DOM toggle, matching existing behavior"
  - "getBulkFiles() getter function added because importers need array reference after reassignment via resetBulkState()"
  - "registerSelectSingleFormat() registration pattern chosen over parameter passing for renderSingleFormats to avoid circular import chain"
  - "renderBulkRow inline onchange removed; initBulkListDelegation() attaches single delegated listener on #bulk-file-list"
  - "api.js re-throws errors with rawDetail property so callers can display structured error messages via buildErrorHtml"

patterns-established:
  - "Registration pattern: export registerX(fn) setter in module A; module B calls registerX at import time to inject callback without circular import"
  - "Event delegation pattern: single listener on container element, use closest('[id^=prefix]') to find row index"
  - "Leaf-first dependency order: state.js → (api.js, ui.js) → feature modules → main.js"

requirements-completed: [UIPX-04]

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 4 Plan 01: Frontend Foundation Modules Summary

**CSS extracted (487 lines) plus state.js, api.js, and ui.js ES modules providing the complete foundation layer for the phase 4 refactor**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-25T03:18:11Z
- **Completed:** 2026-02-25T03:21:27Z
- **Tasks:** 2
- **Files modified:** 4 created

## Accomplishments
- Extracted all CSS from index.html `<style>` block verbatim into `frontend/css/app.css` (487 lines, all design tokens, layout, component styles, responsive breakpoints, animations)
- Created `frontend/js/state.js` as leaf dependency with 7 `export let` state variables and 9 mutation/getter functions including `addToHistory`, `clearHistoryState`, `setBulkFormat`, `getBulkFiles`, `addBulkFile`
- Created `frontend/js/api.js` isolating all 5 `fetch()` calls (`apiUpload`, `apiConvert`, `apiBulkUpload`, `apiBulkConvert`, `apiDownloadUrl`)
- Created `frontend/js/ui.js` with 18 named exports covering all DOM helpers and rendering functions, with circular dependency to `single.js` resolved via registration pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract CSS to app.css and create state.js module** - `a7f75f3` (feat)
2. **Task 2: Create api.js and ui.js modules** - `a336986` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/css/app.css` - All CSS from index.html style block, byte-for-byte copy of 487 lines
- `frontend/js/state.js` - Shared mutable state singleton (leaf dependency, no imports)
- `frontend/js/api.js` - All fetch() calls to /api/* endpoints; imports currentQuality from state.js
- `frontend/js/ui.js` - DOM helpers and rendering functions; imports history/clearHistoryState/setBulkFormat from state.js

## Decisions Made
- `state.js` uses `export let` for all 7 state variables. Since ES module `export let` bindings are read-only from importers, all mutations go through exported functions.
- `setQuality()` kept in `state.js` (not `ui.js`) because it atomically updates both the state value and quality button DOM state — splitting would require callers to invoke two functions every time quality changes.
- `getBulkFiles()` getter added because after `resetBulkState()` reassigns the array reference, importers with a stale binding would see the old empty array. The getter always returns the current reference.
- `registerSelectSingleFormat()` registration pattern chosen over parameter-passing for `renderSingleFormats` to cleanly break the `ui.js` ↔ `single.js` circular import without any runtime overhead.
- Inline `onchange="setBulkFormat(${i}, this.value)"` removed from `renderBulkRow` template; `initBulkListDelegation()` attaches a single delegated listener on `#bulk-file-list` instead.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- All four foundation modules are pure exports with no initialization side-effects
- Import graph is acyclic: `state.js` ← `api.js`, `state.js` ← `ui.js`
- `registerSelectSingleFormat()` must be called by `single.js` before `renderSingleFormats()` is first invoked — documented via JSDoc
- Phase 4 Plan 02 can now create `single.js`, `bulk.js`, and `main.js` that import from these foundation modules

---
*Phase: 04-frontend-es-module-refactor*
*Completed: 2026-02-25*
