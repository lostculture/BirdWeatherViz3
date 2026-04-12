#!/usr/bin/env python3
"""
BirdWeatherViz3 Test Script (Cross-Platform Python)
Automated local dev setup. Works on Windows, macOS, Linux.

Creates an isolated Python venv at backend/.venv and uses bun for the
frontend. No changes to system Python or global npm state.
"""

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser

BLUE, GREEN, YELLOW, RED, NC = (
    "\033[0;34m", "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0m"
)

if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

IS_WIN = sys.platform == "win32"

def header(msg): print(f"\n{BLUE}{'=' * 40}\n{msg}\n{'=' * 40}{NC}\n")
def success(msg): print(f"{GREEN}+ {msg}{NC}")
def error(msg):   print(f"{RED}x {msg}{NC}")
def info(msg):    print(f"{BLUE}> {msg}{NC}")
def warning(msg): print(f"{YELLOW}! {msg}{NC}")

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
VENV = os.path.join(BACKEND, ".venv")

processes = []

def cleanup(*_):
    header("Shutting Down")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try: p.kill()
            except Exception: pass
    success("All servers stopped")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def venv_python():
    return os.path.join(VENV, "Scripts", "python.exe") if IS_WIN \
        else os.path.join(VENV, "bin", "python")

def check_url(url, timeout=5):
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False

def require(binary, install_hint):
    if shutil.which(binary):
        success(f"{binary} is installed")
        return True
    error(f"{binary} is NOT installed")
    print(f"  Install: {install_hint}")
    return False

def main():
    header("BirdWeatherViz3 Test Script")

    header("Checking Dependencies")
    ok = True
    if sys.version_info < (3, 11):
        error(f"Python 3.11+ required (found {sys.version.split()[0]})")
        ok = False
    else:
        success(f"Python {sys.version.split()[0]}")
    ok &= require("bun", "https://bun.sh  |  curl -fsSL https://bun.sh/install | bash")
    if not ok:
        sys.exit(1)

    # ── Backend ──────────────────────────────────────────────────────────
    header("Setting Up Backend")

    env_file = os.path.join(BACKEND, ".env")
    env_example = os.path.join(BACKEND, ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        shutil.copy2(env_example, env_file)
        success(".env created from .env.example")
    else:
        success(".env file already exists")

    for subdir in ("data/db", "data/logs", "data/uploads"):
        os.makedirs(os.path.join(BACKEND, subdir), exist_ok=True)
    success("Data directories ready")

    if not os.path.exists(venv_python()):
        info("Creating Python venv at backend/.venv ...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV])
        success("venv created")
    else:
        success("venv already exists")

    vpy = venv_python()
    try:
        subprocess.check_call(
            [vpy, "-c", "import fastapi, sqlalchemy, plotly"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        success("Backend dependencies already installed")
    except subprocess.CalledProcessError:
        info("Installing backend dependencies into venv ...")
        subprocess.check_call([vpy, "-m", "pip", "install", "-q", "--upgrade", "pip"])
        subprocess.check_call(
            [vpy, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            cwd=BACKEND,
        )
        success("Backend dependencies installed")

    # ── Frontend ─────────────────────────────────────────────────────────
    header("Setting Up Frontend")

    env_file_fe = os.path.join(FRONTEND, ".env")
    env_example_fe = os.path.join(FRONTEND, ".env.example")
    if not os.path.exists(env_file_fe) and os.path.exists(env_example_fe):
        shutil.copy2(env_example_fe, env_file_fe)
        success(".env created from .env.example")
    else:
        success(".env file already exists")

    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        info("Installing frontend dependencies with bun ...")
        subprocess.check_call(["bun", "install", "--frozen-lockfile"], cwd=FRONTEND)
        success("Frontend dependencies installed")
    else:
        success("node_modules already exists")

    # ── Start backend ────────────────────────────────────────────────────
    header("Starting Backend Server")
    info("uvicorn on http://localhost:8000 ...")
    backend_log = open(os.path.join(ROOT, "backend.log"), "w")
    processes.append(subprocess.Popen(
        [vpy, "-m", "uvicorn", "app.main:app", "--reload",
         "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND, stdout=backend_log, stderr=subprocess.STDOUT,
    ))

    for _ in range(20):
        time.sleep(1)
        if check_url("http://localhost:8000/api/v1/health"): break
    else:
        error("Backend failed to start (see backend.log)")
        cleanup()
    success("Backend up on http://localhost:8000")

    # ── Start frontend ───────────────────────────────────────────────────
    header("Starting Frontend Dev Server")
    info("bun run dev on http://localhost:3000 ...")
    frontend_log = open(os.path.join(ROOT, "frontend.log"), "w")
    processes.append(subprocess.Popen(
        ["bun", "run", "dev"],
        cwd=FRONTEND, stdout=frontend_log, stderr=subprocess.STDOUT,
    ))

    for _ in range(20):
        time.sleep(1)
        if check_url("http://localhost:3000"): break
    else:
        warning("Frontend not ready yet (check frontend.log)")
    success("Frontend up on http://localhost:3000")

    header("Opening Browser")
    webbrowser.open("http://localhost:3000")

    header("Servers Running")
    success("Backend:  http://localhost:8000")
    success("Frontend: http://localhost:3000")
    success("API Docs: http://localhost:8000/api/v1/docs")
    warning("Press Ctrl+C to stop")
    print()

    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    error(f"Server exited unexpectedly (PID {p.pid})")
                    cleanup()
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
