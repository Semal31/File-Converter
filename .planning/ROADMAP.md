# Roadmap: File Converter

## Overview

This milestone transforms the existing working-but-rough file converter into a tool that friends, family, or strangers on GitHub can use without hitting broken features or getting confused. The work progresses in strict dependency order: fix the foundation first (broken Docker conversions), then improve error clarity, then add backend progress infrastructure, then refactor the frontend for maintainability, and finally wire everything together with real progress feedback and polished UX.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Docker Reliability** - Fix all broken conversion paths and validate system dependencies in the container (completed 2026-02-24)
- [x] **Phase 2: Error Handling** - Replace raw stack traces and silent failures with human-readable, actionable error messages (completed 2026-02-24)
- [x] **Phase 3: Backend Progress Infrastructure** - Add job registry and SSE endpoint so the frontend has a real signal to consume (completed 2026-02-24)
- [ ] **Phase 4: Frontend ES Module Refactor** - Restructure the monolithic index.html into maintainable ES modules (no behavior change)
- [ ] **Phase 5: Progress Wiring and UI Polish** - Wire SSE progress into the refactored frontend and complete the visual redesign

## Phase Details

### Phase 1: Docker Reliability
**Goal**: Every advertised conversion format works correctly in a fresh Docker container
**Depends on**: Nothing (first phase)
**Requirements**: RELY-01, RELY-02, RELY-03
**Success Criteria** (what must be TRUE):
  1. A user converting .md to PDF in a freshly pulled Docker image gets a valid PDF file, not a 500 error
  2. A file with non-ASCII characters in its name or content converts without encoding errors
  3. Starting the container with a missing system binary (e.g., pandoc removed) prints a clear startup error and exits rather than failing silently on first conversion attempt
  4. The Docker build itself fails (not runtime) if WeasyPrint cannot import — a broken container cannot be pushed
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Fix Dockerfile: add missing WeasyPrint system deps, Noto fonts, UTF-8 ENV, build-time smoke test
- [ ] 01-02-PLAN.md — Add startup binary validation to FastAPI lifespan (pandoc, ffmpeg, weasyprint)
- [ ] 01-03-PLAN.md — Run container smoke tests and human verification of Phase 1 results

### Phase 2: Error Handling
**Goal**: Users see clear, actionable messages when conversions fail instead of raw Python tracebacks
**Depends on**: Phase 1
**Requirements**: ERRH-01, ERRH-02, ERRH-03
**Success Criteria** (what must be TRUE):
  1. A failed single-file conversion shows a plain-English message (e.g., "Conversion failed: unsupported codec") instead of a Python stack trace or ffmpeg stderr dump
  2. A bulk conversion with some failures shows which specific files failed and what went wrong for each, visible in the file list
  3. Uploading a .xyz file shows a message that names the detected format and lists supported alternatives, rather than a generic error
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Add _classify_exc function, custom exception handler, and structured error responses to backend API
- [ ] 02-02-PLAN.md — Update frontend to read data.message, add buildErrorHtml helper with expandable detail toggles

### Phase 3: Backend Progress Infrastructure
**Goal**: The backend can track conversion jobs asynchronously and stream status events to any client that asks
**Depends on**: Phase 1
**Requirements**: PROG-01
**Success Criteria** (what must be TRUE):
  1. POST /api/convert returns a job_id immediately (under 100ms) without waiting for the conversion to finish
  2. GET /api/progress/{job_id} streams SSE events that reflect the actual job state (running, done, error) with the correct download_id on completion
  3. A conversion that fails mid-task surfaces the error through the SSE stream, not as an HTTP 500 on the original POST
  4. A large video conversion that exceeds the previous 300s nginx timeout completes successfully because the HTTP connection is no longer held open
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Add progress dependencies and wire progress_callback through all converter modules
- [ ] 03-02-PLAN.md — Add JOBS registry, SSE endpoint, and convert endpoints to async fire-and-forget

### Phase 4: Frontend ES Module Refactor
**Goal**: The monolithic 56 KB index.html is split into maintainable ES modules with no change to observable behavior
**Depends on**: Phase 1
**Requirements**: UIPX-04
**Success Criteria** (what must be TRUE):
  1. Every feature that worked before the refactor (upload, single convert, bulk convert, history, drag-and-drop) still works identically after it
  2. No inline onclick or onchange attributes remain in index.html — all event handlers use addEventListener
  3. JavaScript is served as separate .js files under js/ and CSS as a separate file under css/ — no inline scripts or styles remain in index.html
  4. The page loads and all interactions work correctly in a browser served by nginx (no file:// protocol required)
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Extract CSS to app.css, create foundation JS modules (state.js, api.js, ui.js)
- [ ] 04-02-PLAN.md — Create feature modules (single.js, bulk.js), wire main.js entry point, strip index.html, verify in browser

### Phase 5: Progress Wiring and UI Polish
**Goal**: Users see real conversion progress, upload progress for large files, and a polished UI that feels like a finished product
**Depends on**: Phase 3, Phase 4
**Requirements**: PROG-02, PROG-03, UIPX-01, UIPX-02, UIPX-03
**Success Criteria** (what must be TRUE):
  1. During a conversion, the UI shows an animated progress indicator that stays active until the SSE stream confirms done — it never jumps to 100% before the file is ready
  2. Uploading a large file shows byte-level upload progress that advances in real time as bytes are sent
  3. The app loads and displays fonts correctly with no internet connection — no requests to Google Fonts CDN
  4. A user converting multiple files in bulk can select a different target format per file before converting, and each row shows its individual success or error status after the batch completes
  5. The dark theme looks visually consistent and polished — spacing, typography, and component states are refined throughout
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

Note: Phases 3 and 4 have no dependency on each other and can be worked in parallel if desired — Phase 3 is backend-only, Phase 4 is frontend structure-only with no behavior change.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Docker Reliability | 3/3 | Complete   | 2026-02-24 |
| 2. Error Handling | 2/2 | Complete    | 2026-02-24 |
| 3. Backend Progress Infrastructure | 2/2 | Complete   | 2026-02-24 |
| 4. Frontend ES Module Refactor | 0/2 | Not started | - |
| 5. Progress Wiring and UI Polish | 0/TBD | Not started | - |
