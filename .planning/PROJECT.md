# File Converter

## What This Is

A self-hosted, Docker-based file converter where users can drop in nearly any file and convert it to another format. It runs offline, supports documents, images, audio, video, data files, and archives through a clean web UI. Built as a public open-source tool that anyone can deploy and use.

## Core Value

Every supported conversion must work reliably — users drop a file in and get a converted file out, every time.

## Requirements

### Validated

- ✓ File upload with format auto-detection — existing
- ✓ Document conversions via pandoc (md, docx, html, etc.) — existing
- ✓ Image conversions via Pillow/CairoSVG — existing
- ✓ Audio conversions via pydub/ffmpeg — existing
- ✓ Video conversions via ffmpeg — existing
- ✓ Data format conversions via pandas (csv, xlsx, json, etc.) — existing
- ✓ Archive handling via py7zr — existing
- ✓ Bulk upload and bulk convert — existing
- ✓ Docker deployment with nginx proxy — existing
- ✓ Drag-and-drop file upload — existing
- ✓ Dark theme UI — existing
- ✓ CI/CD pipeline to Docker Hub — existing

### Active

- [ ] Fix broken format conversions (e.g., .md to PDF fails in Docker)
- [ ] Audit and fix all conversion paths in Docker environment
- [ ] Conversion progress indicators in UI
- [ ] Modern, polished dark theme redesign
- [ ] Improved batch workflow UX (upload many, pick formats, convert all)
- [ ] Quality parameter actually reflected in output where applicable

### Out of Scope

- Mobile native app — web-first, responsive is enough
- User accounts or authentication — it's a stateless tool
- Cloud storage integration — offline/self-hosted is the point
- Real-time collaboration — single-user conversion tool
- File editing — this is a converter, not an editor

## Context

The app already works end-to-end: FastAPI backend with pluggable converter modules, vanilla JS frontend, Docker Compose deployment, and GitHub Actions CI/CD pushing to Docker Hub. The architecture is sound — category-based converter dispatch with async-to-sync bridging for CPU-heavy work.

The main issue is reliability: certain conversion paths fail in the Docker image (confirmed: .md to PDF). This likely stems from missing system dependencies or configuration in the container build. The UI functions but needs polish to feel like a real product — progress feedback, smoother batch workflows, and a more refined visual design.

This is a public/open-source project. The bar is "friends, family, or strangers on GitHub could use it without getting confused or hitting broken features."

## Constraints

- **Deployment**: Must run in Docker — all system dependencies (pandoc, ffmpeg, cairo, etc.) must be present in the container
- **Frontend**: Vanilla HTML/CSS/JS — no build tools or frameworks
- **Offline**: No external API calls — all conversions happen locally
- **Performance**: Large file conversions (video, bulk) need to work without timeouts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vanilla JS frontend (no framework) | Simplicity, no build step, easy to deploy | — Pending |
| FastAPI + pluggable converters | Clean separation, easy to add new formats | ✓ Good |
| In-memory state (no database) | Stateless tool, files are temporary | ✓ Good |
| Docker-first deployment | Self-hosted use case, reproducible environment | ✓ Good |

---
*Last updated: 2026-02-24 after initialization*
