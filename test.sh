#!/usr/bin/env bash
# BirdWeatherViz3 local dev setup (Linux / macOS)
# Creates an isolated Python venv at backend/.venv and uses bun for the
# frontend. Does not touch system Python or global npm state.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
h()  { echo -e "\n${BLUE}========================================${NC}\n${BLUE}$1${NC}\n${BLUE}========================================${NC}\n"; }
ok() { echo -e "${GREEN}✓ $1${NC}"; }
er() { echo -e "${RED}✗ $1${NC}"; }
in_(){ echo -e "${BLUE}ℹ $1${NC}"; }
wa() { echo -e "${YELLOW}⚠ $1${NC}"; }

cleanup() {
    h "Shutting Down"
    [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
    [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
    ok "All servers stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

h "BirdWeatherViz3 Test Script"

h "Checking Dependencies"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q "Python 3"; then
    PY=python
else
    er "Python 3.11+ is NOT installed"; exit 1
fi
PY_VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! $PY -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
    er "Python 3.11+ required (found $PY_VER)"; exit 1
fi
ok "Python $PY_VER"

if ! command -v bun >/dev/null 2>&1; then
    er "bun is NOT installed"
    echo "  Install with: curl -fsSL https://bun.sh/install | bash"
    exit 1
fi
ok "bun $(bun --version)"

# ── Backend ──────────────────────────────────────────────────────────────
h "Setting Up Backend"

if [[ ! -f backend/.env && -f backend/.env.example ]]; then
    cp backend/.env.example backend/.env
    ok ".env created from .env.example"
else
    ok ".env file already exists"
fi

mkdir -p backend/data/db backend/data/logs backend/data/uploads
ok "Data directories ready"

if [[ ! -x backend/.venv/bin/python ]]; then
    in_ "Creating Python venv at backend/.venv ..."
    $PY -m venv backend/.venv
    ok "venv created"
else
    ok "venv already exists"
fi

VPY="$ROOT/backend/.venv/bin/python"
if "$VPY" -c "import fastapi, sqlalchemy, plotly" >/dev/null 2>&1; then
    ok "Backend dependencies already installed"
else
    in_ "Installing backend dependencies into venv ..."
    "$VPY" -m pip install -q --upgrade pip
    (cd backend && "$VPY" -m pip install -q -r requirements.txt)
    ok "Backend dependencies installed"
fi

# ── Frontend ─────────────────────────────────────────────────────────────
h "Setting Up Frontend"

if [[ ! -f frontend/.env && -f frontend/.env.example ]]; then
    cp frontend/.env.example frontend/.env
    ok ".env created from .env.example"
else
    ok ".env file already exists"
fi

if [[ ! -d frontend/node_modules ]]; then
    in_ "Installing frontend dependencies with bun ..."
    (cd frontend && bun install --frozen-lockfile)
    ok "Frontend dependencies installed"
else
    ok "node_modules already exists"
fi

# ── Free ports if something is already bound ─────────────────────────────
free_port() {
    local port="$1" pid=""
    if command -v lsof >/dev/null 2>&1; then
        pid=$(lsof -ti :"$port" 2>/dev/null || true)
    elif command -v ss >/dev/null 2>&1; then
        pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oE 'pid=[0-9]+' | cut -d= -f2 || true)
    fi
    if [[ -n "$pid" ]]; then
        wa "Port $port in use (PID $pid) — killing"
        kill "$pid" 2>/dev/null || true
        sleep 1
        kill -9 "$pid" 2>/dev/null || true
    fi
}
free_port 8000
free_port 3000

# ── Start backend ────────────────────────────────────────────────────────
h "Starting Backend Server"
in_ "uvicorn on http://localhost:8000 ..."
(cd backend && "$VPY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) \
    > backend.log 2>&1 &
BACKEND_PID=$!

for _ in {1..20}; do
    sleep 1
    if curl -sf http://localhost:8000/api/v1/health >/dev/null; then break; fi
done
if ! curl -sf http://localhost:8000/api/v1/health >/dev/null; then
    er "Backend failed to start (see backend.log)"; cleanup
fi
ok "Backend up on http://localhost:8000"

# ── Start frontend ───────────────────────────────────────────────────────
h "Starting Frontend Dev Server"
in_ "bun run dev on http://localhost:3000 ..."
(cd frontend && bun run dev) > frontend.log 2>&1 &
FRONTEND_PID=$!

for _ in {1..20}; do
    sleep 1
    if curl -sf http://localhost:3000 >/dev/null; then break; fi
done
if ! curl -sf http://localhost:3000 >/dev/null; then
    wa "Frontend not ready yet (check frontend.log)"
fi
ok "Frontend up on http://localhost:3000"

# ── Open browser ─────────────────────────────────────────────────────────
h "Opening Browser"
if command -v open >/dev/null 2>&1; then
    open http://localhost:3000
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:3000
else
    wa "Could not auto-open browser"
fi

h "Servers Running"
ok "Backend:  http://localhost:8000"
ok "Frontend: http://localhost:3000"
ok "API Docs: http://localhost:8000/api/v1/docs"
wa "Press Ctrl+C to stop"
echo

wait
