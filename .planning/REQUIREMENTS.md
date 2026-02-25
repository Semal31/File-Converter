# Requirements: File Converter

**Defined:** 2026-02-24
**Core Value:** Every supported conversion must work reliably — users drop a file in and get a converted file out, every time.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Reliability

- [x] **RELY-01**: All advertised conversion paths work correctly in Docker (fix missing libpangoft2, libharfbuzz, font packages)
- [x] **RELY-02**: App validates all required system binaries (pandoc, ffmpeg, cairo) at startup and fails fast with clear message if missing
- [x] **RELY-03**: Docker container has correct UTF-8 locale (LANG=C.UTF-8) for non-ASCII filename and content handling

### Error Handling

- [x] **ERRH-01**: Conversion failures show human-readable error messages instead of raw Python/ffmpeg stack traces
- [x] **ERRH-02**: Bulk conversion shows per-file error detail (which files failed and why)
- [x] **ERRH-03**: Unsupported format errors name the detected format and suggest supported alternatives

### Progress Feedback

- [x] **PROG-01**: Backend supports async job registry with fire-and-forget conversion and SSE progress endpoint
- [x] **PROG-02**: Frontend shows real conversion progress via SSE connection to backend
- [x] **PROG-03**: Frontend shows byte-level upload progress for large files via XHR

### UI Polish

- [x] **UIPX-01**: UI fonts self-hosted as local woff2 files instead of Google Fonts CDN (fixes offline deployments)
- [x] **UIPX-02**: Modern, polished dark theme redesign with consistent spacing and refined components
- [x] **UIPX-03**: Improved batch workflow with per-file format selection, smart defaults, and clear per-item status
- [x] **UIPX-04**: Frontend JS refactored into ES modules (no build step, served as static files via nginx)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Reliability

- **RELY-04**: File size limit enforcement with MAX_UPLOAD_SIZE env var, client-side pre-check, and HTTP 413
- **RELY-05**: Startup probe checks ffmpeg codec availability (libx264, aac, etc.)

### UX Enhancements

- **UIEN-01**: Output file size displayed in success message
- **UIEN-02**: Keyboard accessibility for format selection chips
- **UIEN-03**: Retry failed bulk conversions individually
- **UIEN-04**: Copy-to-clipboard for download URL
- **UIEN-05**: ETA hint for long-running conversions (video, large audio)
- **UIEN-06**: Health indicator showing operational status per converter category

## Out of Scope

| Feature | Reason |
|---------|--------|
| User accounts / authentication | Stateless tool — no user identity needed |
| Persistent conversion history (database) | Files are temporary; no cross-restart state |
| Real-time percent progress for every converter | Only practical for video/ffmpeg; indeterminate for others |
| File editing tools | This is a converter, not an editor |
| Cloud storage integration | Offline/self-hosted is the core identity |
| Job queuing / scheduling UI | Single-instance tool, not a batch processing system |
| PWA / installability | Web app is sufficient |
| Mobile native app | Web-first, responsive is enough |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RELY-01 | Phase 1 | Complete |
| RELY-02 | Phase 1 | Complete |
| RELY-03 | Phase 1 | Complete |
| ERRH-01 | Phase 2 | Complete |
| ERRH-02 | Phase 2 | Complete |
| ERRH-03 | Phase 2 | Complete |
| PROG-01 | Phase 3 | Complete |
| PROG-02 | Phase 5 | Complete |
| PROG-03 | Phase 5 | Complete |
| UIPX-01 | Phase 5 | Complete |
| UIPX-02 | Phase 5 | Complete |
| UIPX-03 | Phase 5 | Complete |
| UIPX-04 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after roadmap creation*
