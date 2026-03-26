#!/usr/bin/env python3
"""
BirdWeatherViz3 Test Script (Cross-Platform Python)
Automated testing script for local development.
Works on Windows, Mac, and Linux.
Version: 1.0.0
"""

import os
import sys
import shutil
import signal
import subprocess
import time
import urllib.request
import urllib.error
import webbrowser

# ── Helpers ──────────────────────────────────────────────────────────────────

BLUE = "\033[0;34m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

# Enable ANSI colours on Windows 10+
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

def header(msg):
    print(f"\n{BLUE}{'=' * 40}")
    print(msg)
    print(f"{'=' * 40}{NC}\n")

def success(msg):
    print(f"{GREEN}\u2713 {msg}{NC}")

def error(msg):
    print(f"{RED}\u2717 {msg}{NC}")

def info(msg):
    print(f"{BLUE}\u2139 {msg}{NC}")

def warning(msg):
    print(f"{YELLOW}\u26A0 {msg}{NC}")


ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

processes = []


def cleanup(*_args):
    header("Shutting Down")
    info("Stopping servers...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    success("All servers stopped")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def run(cmd, cwd=None):
    """Run a command and stream output. Returns exit code."""
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    return result.returncode


def check_url(url, timeout=5):
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    header("BirdWeatherViz3 Test Script")

    # ── Check dependencies ───────────────────────────────────────────────
    header("Checking Dependencies")

    python_cmd = sys.executable  # Use the same Python that's running this script

    if shutil.which("node"):
        success("Node.js is installed")
    else:
        error("Node.js is NOT installed")
        sys.exit(1)

    if shutil.which("npm"):
        success("npm is installed")
    else:
        error("npm is NOT installed")
        sys.exit(1)

    # ── Setup backend ────────────────────────────────────────────────────
    header("Setting Up Backend")

    env_file = os.path.join(BACKEND_DIR, ".env")
    env_example = os.path.join(BACKEND_DIR, ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        info("Creating .env from .env.example...")
        shutil.copy2(env_example, env_file)
        success(".env file created")
    else:
        success(".env file already exists")

    # Create data directories (required for SQLite database, logs, and uploads)
    info("Ensuring data directories exist...")
    for subdir in ("data/db", "data/logs", "data/uploads"):
        os.makedirs(os.path.join(BACKEND_DIR, subdir), exist_ok=True)
    success("Data directories ready")

    # Check / install Python dependencies
    info("Checking Python dependencies...")
    rc = subprocess.run(
        [python_cmd, "-c", "import fastapi, sqlalchemy, plotly"],
        capture_output=True,
    ).returncode
    if rc == 0:
        success("Backend dependencies are installed")
    else:
        warning("Some backend dependencies missing")
        info("Installing backend dependencies...")
        run(f'"{python_cmd}" -m pip install -r requirements.txt', cwd=BACKEND_DIR)

    # ── Setup frontend ───────────────────────────────────────────────────
    header("Setting Up Frontend")

    env_file_fe = os.path.join(FRONTEND_DIR, ".env")
    env_example_fe = os.path.join(FRONTEND_DIR, ".env.example")
    if not os.path.exists(env_file_fe) and os.path.exists(env_example_fe):
        info("Creating .env from .env.example...")
        shutil.copy2(env_example_fe, env_file_fe)
        success(".env file created")
    else:
        success(".env file already exists")

    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.isdir(node_modules):
        warning("node_modules not found")
        info("Installing frontend dependencies...")
        run("npm install", cwd=FRONTEND_DIR)
        success("Frontend dependencies installed")
    else:
        success("node_modules already exists")

    # ── Start backend ────────────────────────────────────────────────────
    header("Starting Backend Server")

    info("Starting uvicorn on http://localhost:8000...")
    backend_log = open(os.path.join(ROOT, "backend.log"), "w")
    backend_proc = subprocess.Popen(
        [python_cmd, "-m", "uvicorn", "app.main:app", "--reload",
         "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=backend_log,
        stderr=subprocess.STDOUT,
    )
    processes.append(backend_proc)

    info("Waiting for backend to start...")
    for _ in range(10):
        time.sleep(1)
        if check_url("http://localhost:8000/api/v1/health"):
            break
    else:
        error("Backend failed to start (check backend.log)")
        cleanup()

    success("Backend is running at http://localhost:8000")
    info("API docs available at http://localhost:8000/api/v1/docs")

    # ── Start frontend ───────────────────────────────────────────────────
    header("Starting Frontend Dev Server")

    info("Starting Vite dev server on http://localhost:3000...")
    frontend_log = open(os.path.join(ROOT, "frontend.log"), "w")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
    )
    processes.append(frontend_proc)

    info("Waiting for frontend to start...")
    for _ in range(15):
        time.sleep(1)
        if check_url("http://localhost:3000"):
            break
    else:
        warning("Frontend might not be ready yet (check frontend.log)")

    success("Frontend is running at http://localhost:3000")

    # ── Open browser ─────────────────────────────────────────────────────
    header("Opening Browser")
    info("Opening http://localhost:3000 in your browser...")
    webbrowser.open("http://localhost:3000")

    # ── Keep running ─────────────────────────────────────────────────────
    header("Servers Running")
    success("Backend:  http://localhost:8000")
    success("Frontend: http://localhost:3000")
    success("API Docs: http://localhost:8000/api/v1/docs")
    print()
    warning("Press Ctrl+C to stop all servers")
    print()
    info("Logs available in backend.log and frontend.log")

    # Wait until a process exits or user presses Ctrl+C
    try:
        while True:
            for proc in processes:
                if proc.poll() is not None:
                    error(f"A server stopped unexpectedly (PID {proc.pid})")
                    cleanup()
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
