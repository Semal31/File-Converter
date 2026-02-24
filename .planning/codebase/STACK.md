# Technology Stack

**Analysis Date:** 2026-02-24

## Languages

**Primary:**
- Python 3.12 - Backend API and all file conversion logic

**Secondary:**
- HTML/CSS/JavaScript (Vanilla) - Frontend SPA with no frameworks or build tools

## Runtime

**Environment:**
- Python 3.12 (with slim-bookworm base in Docker)

**Package Manager:**
- pip (Python)
- Docker & Docker Compose for containerization

**Lockfile:**
- `requirements.txt` (pinned versions present)

## Frameworks

**Core:**
- FastAPI 0.110.0+ - REST API server
- Uvicorn 0.27.0+ - ASGI server (runs FastAPI)

**Web Server:**
- Nginx - Frontend proxy/load balancer (Docker deployment only)

**Frontend:**
- Vanilla HTML/CSS/JavaScript - Single-page application with no framework dependencies

## Key Dependencies

**Critical (File Conversion):**
- `pypandoc` 1.13+ - Document format conversions (wraps pandoc binary)
- `weasyprint` 61.0+ - HTML to PDF conversion fallback
- `Pillow` 10.2.0+ - Image processing and raster conversions
- `cairosvg` 2.7.1+ - SVG to raster conversion
- `pydub` 0.25.1+ - Audio format conversions (wraps ffmpeg)
- `ffmpeg-python` 0.2+ - Video format conversions (wraps ffmpeg binary)
- `pandas` 2.2.0+ - Data/spreadsheet conversions
- `openpyxl` 3.1.2+ - Excel file handling
- `PyYAML` 6.0.1+ - YAML parsing/generation
- `lxml` 5.1.0+ - XML parsing and manipulation
- `py7zr` 0.20.8+ - 7z archive handling

**Core Utilities:**
- `python-multipart` 0.0.9+ - Multipart form parsing for file uploads
- `markdown` 3.5.2+ - Markdown parsing

## System Dependencies

**Required External Binaries:**
- `pandoc` - Document format conversion engine (Ubuntu: `pandoc`, macOS: `brew install pandoc`)
- `ffmpeg` - Audio/video conversion engine (Ubuntu: `ffmpeg`, macOS: `brew install ffmpeg`)
- `libcairo2` - Cairo rendering library for cairosvg (Ubuntu: `libcairo2`, macOS: `brew install cairo`)
- `libpango-1.0-0` - Pango text layout (Ubuntu: `libpango-1.0-0`, macOS: `brew install pango`)
- `libpangocairo-1.0-0` - Pango Cairo bindings (Ubuntu: `libpangocairo-1.0-0`)
- `libgdk-pixbuf2.0-0` - Image loading library (Ubuntu: `libgdk-pixbuf2.0-0`)
- `libffi-dev` - Foreign function interface (Ubuntu: `libffi-dev`)
- `shared-mime-type` - MIME type detection (Ubuntu: `shared-mime-info`)
- `fonts-liberation` - Font files for rendering (Ubuntu: `fonts-liberation`)

## Configuration

**Environment Variables:**
- `PORT` - Server port (default: 8070)
- `.env` files - Not used; no environment configuration required for basic setup

**Application Config:**
- File cleanup TTL: 1 hour (hardcoded in `backend/main.py` as `FILE_TTL = 3600`)
- Cleanup interval: 5 minutes (hardcoded as `CLEANUP_INTERVAL = 300`)
- Temporary directory: System `tempfile` directory with `fc_` prefix
- CORS: Enabled for all origins (development-friendly)

**Build Configuration:**
- `Dockerfile` - Python 3.12-slim base with system dependencies pre-installed
- `docker-compose.yml` - Services: backend (8070), frontend/nginx (8071)
- `nginx.conf` - Frontend SPA serving and API reverse proxy

## Platform Requirements

**Development:**
- Python 3.12+
- System dependencies: pandoc, ffmpeg, cairo, pango (see System Dependencies above)
- Bash shell (`run.sh` for local startup)

**Production:**
- Docker & Docker Compose
- Nginx (included in Docker Compose)
- 512MB+ available client request size (configured in nginx.conf)
- 300s+ timeout for long-running conversions (video/large audio)

## Deployment

**Docker Build:**
- Base: `python:3.12-slim-bookworm`
- Backend port: 8070 (internal to Docker), proxied via nginx
- Frontend port: 8071 via nginx (external)
- Health check: `curl -f http://localhost:8070/api/health` every 10s
- Restart policy: unless-stopped

**CI/CD:**
- Platform: GitHub Actions
- Pipeline: `.github/workflows/docker.yml`
- Trigger: Push to `main` branch
- Actions: Docker build → push to Docker Hub (`semal31/file-converter`)
- Caching: GitHub Actions cache for Docker layers

---

*Stack analysis: 2026-02-24*
