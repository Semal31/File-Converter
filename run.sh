#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  File Converter — start script
#  http://localhost:8070  (FastAPI serves both API and frontend)
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$SCRIPT_DIR/.venv"
PORT="${PORT:-8070}"

# ── Colours ──────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[fc]${RESET} $*"; }
success() { echo -e "${GREEN}[fc]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[fc]${RESET} $*"; }

# ── Dependency checks ─────────────────────────────────────────
check_dep() {
  command -v "$1" >/dev/null 2>&1 || { warn "Warning: '$1' not found — some conversions may fail."; }
}

info "Checking system dependencies..."
check_dep pandoc
check_dep ffmpeg

# ── Python venv ───────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating Python virtual environment at $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi

info "Installing / updating Python dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"

success "Dependencies ready."

# ── Start server ─────────────────────────────────────────────
success "File Converter is running!"
echo ""
echo -e "  App      → ${CYAN}http://localhost:$PORT${RESET}"
echo -e "  API docs → ${CYAN}http://localhost:$PORT/docs${RESET}"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

cd "$BACKEND_DIR"
exec "$VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port "$PORT" --reload --log-level info
