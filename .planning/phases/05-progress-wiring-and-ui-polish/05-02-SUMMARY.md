---
phase: 05-progress-wiring-and-ui-polish
plan: 02
subsystem: api-transport
tags: [api, xhr, sse, nginx, progress, bulk-download, zip]
dependency_graph:
  requires: []
  provides: [apiUploadWithProgress, watchJobProgress, apiBulkUploadWithProgress, apiBulkDownloadZip, SSE-nginx-proxy, bulk-download-zip-endpoint]
  affects: [frontend/js/single.js, frontend/js/bulk.js]
tech_stack:
  added: [zipfile, io]
  patterns: [XHR-upload-progress, EventSource-SSE, nginx-SSE-proxy, in-memory-ZIP]
key_files:
  created: []
  modified:
    - frontend/js/api.js
    - nginx.conf
    - backend/main.py
decisions:
  - "watchJobProgress uses 'message' event listener (not named events) because backend SSE uses unnamed events (no event: field)"
  - "apiBulkDownloadZip uses hidden <a> click (not fetch/XHR) because backend streams a file — browser handles Content-Disposition natively"
  - "apiBulkUploadWithProgress uploads files sequentially (not concurrently) to avoid server overload; each gets its own XHR for per-file progress"
  - "bulk-download-zip builds ZIP in memory (not streaming chunks) because files are already on disk and bounded in size"
  - "GET endpoint with repeated ?ids= query params (not POST with JSON body) so frontend can trigger with a plain <a> href click"
metrics:
  duration: "~2 min"
  completed: "2026-02-25"
  tasks: 3
  files_modified: 3
---

# Phase 05 Plan 02: API Transport Layer Summary

XHR upload with progress callbacks, EventSource SSE consumer with clean close, nginx SSE proxy with buffering off, and backend in-memory ZIP endpoint for bulk download.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add XHR upload and EventSource SSE functions to api.js | 48f7a7f | frontend/js/api.js |
| 2 | Add nginx SSE proxy configuration | 15f529d | nginx.conf |
| 3 | Add /api/bulk-download-zip backend endpoint | fe6c717 | backend/main.py |

## What Was Built

### Task 1: api.js — Four new exports

**`apiUploadWithProgress(file, onProgress)`**
XHR-based upload that reports upload ratio (0.0-1.0) via `onProgress`. The `xhr.upload.addEventListener('progress', ...)` is registered before `xhr.send()` (required order). Error objects carry `.rawDetail` for compatibility with existing `buildErrorHtml` function.

**`watchJobProgress(jobId, onProgress)`**
EventSource SSE consumer that listens on the `'message'` event (not named events like `'done'` or `'running'`) because the backend streams unnamed SSE events. Calls `es.close()` in both `done` and `error` terminal states to prevent browser auto-reconnect loops.

**`apiBulkUploadWithProgress(files, onFileProgress)`**
Uploads files sequentially via `apiUploadWithProgress`, calling `onFileProgress(fileIndex, ratio)` for each file. Return shape `{files: [...], count: N}` matches the existing `apiBulkUpload` response for backward compatibility. Sequential (not parallel) to avoid overwhelming the server.

**`apiBulkDownloadZip(downloadIds)`**
Builds a GET URL with repeated `?ids=` query params and triggers a browser download via a hidden `<a>` element click. No fetch/XHR needed — the backend responds with `Content-Disposition: attachment` which the browser handles natively.

**Removed:** `import { currentQuality } from './state.js'` — this import was unused in api.js (quality is passed as a parameter to `apiConvert` and `apiBulkConvert`).

All 5 existing exports preserved: `apiUpload`, `apiConvert`, `apiBulkUpload`, `apiBulkConvert`, `apiDownloadUrl`.

### Task 2: nginx.conf — SSE proxy location

Added `/api/progress/` location block before the general `/api/` block. Key settings:
- `proxy_buffering off` — prevents nginx from batching SSE events into a buffer
- `proxy_cache off` — prevents caching of SSE responses
- `proxy_http_version 1.1` — required for chunked transfer encoding used by SSE
- `proxy_set_header Connection ''` — clears Connection header to avoid `close` behavior
- `proxy_read_timeout 300s` — allows long-running video conversions

Nginx prefix matching ensures `/api/progress/` takes priority over `/api/` without any regex.

### Task 3: backend/main.py — GET /api/bulk-download-zip

New endpoint accepting `List[str]` via repeated `?ids=` query params (FastAPI parses this automatically). Key behavior:
- **Silent skip:** Missing or expired download_ids are skipped — ZIP contains only found files
- **Filename deduplication:** `file.pdf` collision becomes `file (2).pdf` via `str.rpartition('.')`
- **In-memory ZIP:** `zipfile.ZipFile` with `ZIP_DEFLATED` compression, built in `io.BytesIO`
- **Response:** Raw `Response` with `Content-Disposition: attachment` and `Content-Length`
- Added `io` and `zipfile` stdlib imports; `Response` added to existing `fastapi.responses` import

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| frontend/js/api.js | FOUND |
| nginx.conf | FOUND |
| backend/main.py | FOUND |
| 05-02-SUMMARY.md | FOUND |
| commit 48f7a7f (Task 1) | FOUND |
| commit 15f529d (Task 2) | FOUND |
| commit fe6c717 (Task 3) | FOUND |
