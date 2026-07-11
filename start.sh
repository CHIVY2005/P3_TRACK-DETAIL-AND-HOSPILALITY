#!/usr/bin/env bash
#
# Guardian Pricing OS — khoi dong ca backend (FastAPI) va frontend (Vite) cung luc.
# Usage:
#   ./start.sh            # chay ca hai, log ra terminal
#   BACKEND_PORT=9000 ./start.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8001}"   # frontend goi mac dinh port 8001 (xem frontend/src/api.js)
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Chon lenh mo trinh duyet (khong bat buoc)
info()  { printf '\033[1;33m[guardian]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[guardian]\033[0m %s\n' "$*" >&2; }

# --- Kiem tra moi truong ------------------------------------------------------
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { error "Khong tim thay $PYTHON_BIN"; exit 1; }
command -v npm >/dev/null 2>&1          || { error "Khong tim thay npm (can Node.js)"; exit 1; }

# --- Cai dependency neu thieu -------------------------------------------------
if ! "$PYTHON_BIN" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  info "Backend thieu dependency -> pip install -r requirements.txt"
  "$PYTHON_BIN" -m pip install -r "$BACKEND_DIR/requirements.txt"
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  info "Frontend chua co node_modules -> npm install"
  (cd "$FRONTEND_DIR" && npm install)
fi

# --- Giai phong port neu dang bi chiem ----------------------------------------
free_port() {
  local port="$1" pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "$port/tcp" 2>/dev/null || true)"
  fi
  if [ -n "$pids" ]; then
    info "Port $port dang bi chiem -> giai phong (kill $pids)"
    kill $pids >/dev/null 2>&1 || true
    sleep 1
  fi
}
free_port "$BACKEND_PORT"
free_port "$FRONTEND_PORT"

# --- Don dep tien trinh con khi thoat -----------------------------------------
PIDS=()
cleanup() {
  info "Dang dung backend + frontend..."
  for pid in "${PIDS[@]:-}"; do
    [ -n "${pid:-}" ] && kill "$pid" >/dev/null 2>&1 || true
  done
  wait >/dev/null 2>&1 || true
  info "Da dung. Tam biet."
}
trap cleanup INT TERM EXIT

# --- Backend ------------------------------------------------------------------
# Bat auto-reload khi sua code bang: RELOAD=1 ./start.sh
RELOAD_FLAG=()
[ "${RELOAD:-0}" = "1" ] && RELOAD_FLAG=(--reload)

info "Khoi dong BACKEND  -> http://localhost:$BACKEND_PORT  (docs: /docs)"
(
  cd "$BACKEND_DIR"
  exec "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" "${RELOAD_FLAG[@]}"
) &
PIDS+=("$!")

# --- Frontend -----------------------------------------------------------------
info "Khoi dong FRONTEND -> http://localhost:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  exec npm run dev -- --port "$FRONTEND_PORT"
) &
PIDS+=("$!")

info "Ca hai dang chay. Nhan Ctrl+C de dung tat ca."

# Neu 1 trong 2 tien trinh chet, dung ca script (va trap cleanup se don not)
wait -n
error "Mot tien trinh da dung -> tat ca dang duoc don dep."
