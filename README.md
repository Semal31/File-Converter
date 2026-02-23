# File Converter

A self-hosted, full-stack file conversion tool. Drop a file, pick an output format, download the result. No cloud, no tracking.

**Backend:** FastAPI (Python 3.12) · **Frontend:** Vanilla HTML/CSS/JS (Glacier + Dusk theme)

---

## Features

| Category    | Input formats                        | Output formats                       |
|-------------|--------------------------------------|--------------------------------------|
| Documents   | DOCX, TXT, MD, HTML                  | PDF, DOCX, TXT, MD, HTML             |
| Images      | PNG, JPG, WEBP, BMP, GIF, TIFF, ICO, SVG | PNG, JPG, WEBP, BMP, GIF, TIFF, ICO |
| Audio       | MP3, WAV, OGG, FLAC, AAC, M4A        | MP3, WAV, OGG, FLAC, AAC, M4A        |
| Video       | MP4, MKV, AVI, WEBM, MOV, GIF        | MP4, MKV, AVI, WEBM, MOV, GIF        |
| Data        | CSV, JSON, XLSX, XML, YAML, TSV      | CSV, JSON, XLSX, XML, YAML, TSV      |
| Archives    | ZIP, TAR, TAR.GZ, 7Z                 | ZIP, TAR, TAR.GZ, 7Z                 |

- Auto-detects input format from file extension
- Uploaded files and conversions cleaned up automatically after 1 hour
- Session history and stats in the sidebar
- FastAPI `/docs` interactive API explorer

---

## Quick Start (local, no Docker)

### Prerequisites

```bash
# Ubuntu / Debian
sudo apt install pandoc ffmpeg libcairo2 libpango-1.0-0 fonts-liberation

# macOS (Homebrew)
brew install pandoc ffmpeg cairo pango
```

Python 3.12+ is required.

### Run

```bash
cd /path/to/file-converter
chmod +x run.sh
./run.sh
```

- App: http://localhost:8070
- API docs: http://localhost:8070/docs

Custom port:

```bash
PORT=9000 ./run.sh
```

---

## Docker (recommended for production)

```bash
cd /path/to/file-converter
docker compose up --build
```

Services:
- `frontend` — nginx serving the SPA on port **8071**, proxies `/api/*` to backend (no CORS issues)
- `backend` — uvicorn FastAPI app on port **8070**

---

## Project Structure

```
file-converter/
├── backend/
│   ├── main.py                   # FastAPI app — upload / convert / download endpoints
│   ├── requirements.txt
│   ├── Dockerfile
│   └── converters/
│       ├── __init__.py           # format detection, routing
│       ├── base.py               # BaseConverter interface
│       ├── documents.py          # pandoc + weasyprint
│       ├── images.py             # Pillow + cairosvg
│       ├── audio.py              # pydub + ffmpeg
│       ├── video.py              # ffmpeg-python
│       ├── data.py               # pandas + PyYAML
│       └── archives.py           # zipfile + tarfile + py7zr
├── frontend/
│   └── index.html                # Single-file SPA
├── nginx.conf                    # Nginx config for Docker frontend
├── docker-compose.yml
├── run.sh                        # Local dev start script
└── README.md
```

---

## API Reference

```
GET  /api/health
     → { status, version }

POST /api/upload
     body: multipart/form-data  file=<binary>
     → { file_id, filename, size, detected_format, category, available_formats }

POST /api/convert
     body: form  file_id=<uuid>  target_format=<string>  quality=<string>
     quality: "original" (default) | "high" | "medium" | "low" | "lossless"
     → { download_id, output_filename, status }

POST /api/bulk-upload
     body: multipart/form-data  files=<binary[]>
     → { files: [{ file_id, filename, size, detected_format, category, available_formats }], count }

POST /api/bulk-convert
     body: form  conversions=<json array>  quality=<string>
     conversions: [{ file_id, target_format }, ...]
     → { download_id, output_filename, count, errors }

GET  /api/download/{download_id}
     → file stream (application/octet-stream)
     Note: file is deleted after download.
```

Full interactive docs at `/docs` when the backend is running.

---

## Notes

- **PDF** is output-only (pandoc cannot read PDFs). Uses WeasyPrint (HTML → PDF pipeline). Complex DOCX layouts may not render perfectly; install `pandoc` + `texlive` for LaTeX-based PDF if needed.
- **SVG input** is supported (cairosvg rasterises to PNG first). SVG *output* from raster images is not supported.
- **Video / audio** conversions require `ffmpeg` on `PATH`. The Docker image includes it.
- **Archive repacking** extracts the source and repacks — very large archives may be slow.
- Temp files live in a system temp directory and are removed after 1 hour or after download, whichever comes first.
