# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every supported conversion must work reliably — users drop a file in and get a converted file out, every time.
**Current focus:** Phase 5 — Frontend Polish (next)

## Current Position

Phase: 5 of 5 (Progress Wiring and UI Polish)
Plan: 4 of 5 in current phase — COMPLETE
Status: Phase 5 in progress — Plan 04 complete (bulk workflow overhaul: per-file apiConvert + SSE tracking, X remove buttons, per-row Download buttons, smart defaults, summary banner, Download All ZIP)
Last activity: 2026-02-25 — Plan 05-04 complete (renderBulkRow with progress bars/X/Download; convertBulk per-file apiConvert + Promise.allSettled SSE; summary banner; Download All ZIP button)

Progress: [█████████░] 90%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: ~5 min
- Total execution time: ~46 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-docker-reliability | 3 | ~18 min | ~6 min |

**Recent Trend:**
- Last 5 plans: 01-01 (2 min), 01-02 (1 min), 01-03 (15 min)
- Trend: On track

*Updated after each plan completion*
| Phase 01-docker-reliability P03 | ~15min | 2 tasks | 0 files |
| Phase 01-docker-reliability P02 | 1 | 1 tasks | 1 files |
| Phase 01-docker-reliability P01 | 2 | 1 tasks | 1 files |
| Phase 02-error-handling P01 | 3min | 2 tasks | 2 files |
| Phase 02-error-handling P02 | 2min | 1 tasks | 1 files |
| Phase 03-backend-progress-infrastructure P01 | 4min | 2 tasks | 8 files |
| Phase 03-backend-progress-infrastructure P02 | 3min | 2 tasks | 1 files |
| Phase 04-frontend-es-module-refactor P01 | 3min | 2 tasks | 4 files |
| Phase 04-frontend-es-module-refactor P02 | ~25min | 3 tasks | 5 files |
| Phase 05-progress-wiring-and-ui-polish P01 | ~3min | 2 tasks | 4 files |
| Phase 05-progress-wiring-and-ui-polish P02 | ~2min | 3 tasks | 3 files |
| Phase 05-progress-wiring-and-ui-polish P03 | ~1min | 2 tasks | 3 files |
| Phase 05-progress-wiring-and-ui-polish P04 | 2min | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Phases 3 and 4 (backend SSE infrastructure and frontend ES module refactor) have no shared files and can be worked in parallel if desired.
- Roadmap: UIPX-01 (self-hosted fonts) assigned to Phase 5 alongside the other frontend polish work rather than as a standalone phase — it is a quick change that fits naturally with the CSS/font work already happening there.
- [Phase 01-docker-reliability]: Use os._exit(1) not sys.exit() in startup validation — uvicorn catches SystemExit but os._exit bypasses all exception handlers unconditionally
- [Phase 01-docker-reliability]: Use shutil.which() for binary checks (not subprocess) — simpler stdlib approach already available in main.py imports
- [Phase 01-docker-reliability]: Used fonts-noto-core (not fonts-noto metapackage) to add Unicode coverage without pulling 500MB+ CJK fonts
- [Phase 01-docker-reliability]: Added RUN python -c 'import weasyprint' build-time smoke test so broken images fail at docker build rather than on first user request
- [Phase 01-docker-reliability]: Phase 1 complete — all RELY-01, RELY-02, RELY-03 confirmed end-to-end in container via 7-step smoke test (human approved 2026-02-24)
- [Phase 02-error-handling]: Unsupported extension error names only the bad extension without listing alternatives (user decision locked)
- [Phase 02-error-handling]: Invalid conversion target error lists available targets with uppercase format names and Available targets: prefix
- [Phase 02-error-handling]: _classify_exc uses lazy imports to match existing codebase pattern and avoid failures if optional library absent
- [Phase 02-error-handling]: Frontend displays API message directly; raw detail hidden behind Show details toggle using <details>/<summary>
- [Phase 03-backend-progress-infrastructure]: VideoConverter: replaced ffmpeg-python fluent API with raw CLI + FfmpegProgress for real 0-100% progress reporting
- [Phase 03-backend-progress-infrastructure]: GIF two-pass encoding uses subprocess.run with stage-based 30/99 progress (FfmpegProgress tracks single process only)
- [Phase 03-backend-progress-infrastructure]: progress_callback always optional (default None), guarded with if progress_callback — backward compatible with existing callers
- [Phase 03-backend-progress-infrastructure]: POST /api/convert and /api/bulk-convert break frontend contract intentionally — Phase 5 will update frontend to consume job_id + SSE
- [Phase 03-backend-progress-infrastructure]: Two-pass bulk validation: PASS 1 collects validated/errors with no side effects; PASS 2 spawns jobs — prevents interleaved spawning when some items fail validation
- [Phase 04-frontend-es-module-refactor]: state.js uses export let for all state vars; mutation functions exported separately since importers cannot reassign export let bindings
- [Phase 04-frontend-es-module-refactor]: registerSelectSingleFormat() registration pattern chosen to break ui.js <> single.js circular import without parameter passing
- [Phase 04-frontend-es-module-refactor]: renderBulkRow inline onchange removed; initBulkListDelegation() attaches single delegated listener on #bulk-file-list
- [Phase 04-frontend-es-module-refactor]: single.js imports uploadBulk from bulk.js directly (acyclic: single->bulk, no reverse) — handleFiles routing stays clean without registration pattern
- [Phase 04-frontend-es-module-refactor]: setSingleFormat() added to state.js to allow selectSingleFormat in single.js to update only the format field without resetting file_id/category/fmts
- [Phase 05-progress-wiring-and-ui-polish]: Self-hosted fonts via Fontsource CDN woff2 variable files; no Google Fonts CDN dependency (UIPX-01)
- [Phase 05-progress-wiring-and-ui-polish]: Emerald #10b981 as primary accent replacing Glacier cyan #CBF3F0; --secondary removed (was only badge-doc)
- [Phase 05-progress-wiring-and-ui-polish]: Body font switched to Inter Variable at 14px from monospace for readability; monospace reserved for chips/selects/code UI
- [Phase 05-progress-wiring-and-ui-polish]: watchJobProgress uses 'message' event listener (not named events) because backend SSE uses unnamed events (no event: field in stream)
- [Phase 05-progress-wiring-and-ui-polish]: apiBulkDownloadZip uses hidden <a> click (not fetch/XHR) — backend streams file with Content-Disposition: attachment; browser handles natively
- [Phase 05-progress-wiring-and-ui-polish]: apiBulkUploadWithProgress uploads files sequentially (not concurrently) to avoid server overload; each gets own XHR for accurate per-file progress
- [Phase 05-progress-wiring-and-ui-polish]: bulk-download-zip GET endpoint with repeated ?ids= query params (not POST/JSON) so frontend triggers download with plain <a> href/click
- [Phase 05-progress-wiring-and-ui-polish]: Upload phase maps XHR ratio (0-1) to bar (0-50%); SSE percent (0-99) maps to bar (50-100%); done event sets 100%
- [Phase 05-progress-wiring-and-ui-polish]: Output filename derived from original name + target format (backend Phase 3 contract returns only {job_id} from /api/convert, not output_filename)
- [Phase 05-progress-wiring-and-ui-polish]: Download button shown on completion, no auto-download per user decision
- [Phase 05-progress-wiring-and-ui-polish]: Per-file apiConvert (not apiBulkConvert) gives one job_id per file for independent SSE tracking in bulk mode
- [Phase 05-progress-wiring-and-ui-polish]: Promise.allSettled opens all bulk SSE connections simultaneously — rows update independently without blocking
- [Phase 05-progress-wiring-and-ui-polish]: Smart format default: renderBulkRow sets target_format to first available_formats entry if none set

### Pending Todos

None yet.

### Blockers/Concerns

- [RESOLVED 2026-02-24] Phase 1: `fonts-noto-core` package name — confirmed valid in Debian Bookworm (smoke test verified fonts present in container)
- [RESOLVED 2026-02-24] Phase 1: ffmpeg codec availability — ffmpeg libx264 confirmed available in Debian Bookworm apt package via smoke test
- [RESOLVED 2026-02-25] Phase 4: Inline handler audit scope — renderBulkRow onchange removed in 04-01; remaining onclick handlers will be wired in main.js/single.js/bulk.js in 04-02.

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 05-04-PLAN.md — bulk workflow overhaul complete; per-file apiConvert + Promise.allSettled SSE tracking; X remove buttons; per-row Download buttons; smart format defaults; summary banner; Download All ZIP button.
Resume file: None
