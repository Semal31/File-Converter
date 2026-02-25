# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every supported conversion must work reliably — users drop a file in and get a converted file out, every time.
**Current focus:** Phase 5 — Frontend Polish (next)

## Current Position

Phase: 4 of 5 (Frontend ES Module Refactor) — COMPLETE
Plan: 2 of 2 in current phase — COMPLETE
Status: Phase 4 complete — all plans done; ready for Phase 5
Last activity: 2026-02-25 — Plan 04-02 complete (single.js, bulk.js, main.js created; index.html stripped to clean HTML shell; all 15 browser verification items passed by human)

Progress: [████████░░] 80%

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

### Pending Todos

None yet.

### Blockers/Concerns

- [RESOLVED 2026-02-24] Phase 1: `fonts-noto-core` package name — confirmed valid in Debian Bookworm (smoke test verified fonts present in container)
- [RESOLVED 2026-02-24] Phase 1: ffmpeg codec availability — ffmpeg libx264 confirmed available in Debian Bookworm apt package via smoke test
- [RESOLVED 2026-02-25] Phase 4: Inline handler audit scope — renderBulkRow onchange removed in 04-01; remaining onclick handlers will be wired in main.js/single.js/bulk.js in 04-02.

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 04-02-PLAN.md — single.js, bulk.js, main.js created; index.html stripped to clean HTML shell; Phase 4 ES module refactor fully complete with human browser verification passed.
Resume file: None
