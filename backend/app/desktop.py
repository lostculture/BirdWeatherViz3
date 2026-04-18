"""
BirdWeatherViz3 Desktop Launcher

Launches the FastAPI backend in a background thread and opens a native
window via pywebview.  All data is stored in the OS-standard per-user
data directory (via platformdirs).

Usage:
    python -m app.desktop          # from backend/
    python backend/app/desktop.py  # from repo root
"""

import logging
import os
import shutil
import socket
import sys
import threading
import time

import platformdirs
import uvicorn

APP_NAME = "BirdWeatherViz3"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _find_free_port() -> int:
    """Bind to port 0 on localhost — the OS assigns a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _resolve_data_dir() -> str:
    """Return (and create) the per-user data directory."""
    data_dir = platformdirs.user_data_dir(APP_NAME, appauthor=False)
    for sub in ("db", "logs", "uploads"):
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)
    return data_dir


def _resolve_frontend_dist() -> str:
    """Locate the built frontend dist directory."""
    # When running from source
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"),
        # When bundled by PyInstaller
        os.path.join(getattr(sys, "_MEIPASS", ""), "frontend", "dist"),
    ]
    for candidate in candidates:
        resolved = os.path.abspath(candidate)
        if os.path.isdir(resolved) and os.path.isfile(os.path.join(resolved, "index.html")):
            return resolved
    # Fallback — let main.py warn if missing
    return os.path.abspath(candidates[0])


def _maybe_migrate_data(data_dir: str) -> None:
    """
    First-run helper: if the user-data-dir DB doesn't exist but a
    local ./data/db/birdweather.db does, copy it over so the user
    keeps their existing data when switching from Docker/web to desktop.
    """
    dest_db = os.path.join(data_dir, "db", "birdweather.db")
    if os.path.exists(dest_db):
        return

    source_db = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "db", "birdweather.db")
    )
    if os.path.isfile(source_db):
        logging.info("First run: copying existing database to %s", dest_db)
        shutil.copy2(source_db, dest_db)


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    """Poll localhost:<port>/api/v1/health until it responds or timeout."""
    import urllib.request
    import urllib.error

    url = f"http://127.0.0.1:{port}/api/v1/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.25)
    return False


def main() -> None:
    # --- Fix windowed mode streams --------------------------------------
    # PyInstaller's --windowed mode (runw.exe) sets sys.stdout/stderr to None.
    # Uvicorn's logging calls stream.isatty() which crashes on None.
    # Redirect to devnull so logging and isatty() calls work.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    # --- Resolve paths --------------------------------------------------
    data_dir = _resolve_data_dir()
    log_dir = os.path.join(data_dir, "logs")
    db_path = os.path.join(data_dir, "db", "birdweather.db")
    dist_dir = _resolve_frontend_dist()
    port = _find_free_port()

    # --- Configure logging ----------------------------------------------
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "desktop.log"), encoding="utf-8"),
        ],
    )
    logger = logging.getLogger("desktop")
    logger.info("Data directory : %s", data_dir)
    logger.info("Database       : %s", db_path)
    logger.info("Frontend dist  : %s", dist_dir)
    logger.info("Port           : %d", port)

    # --- First-run migration --------------------------------------------
    _maybe_migrate_data(data_dir)

    # --- Set env vars BEFORE importing the FastAPI app -------------------
    os.environ["BWV_MODE"] = "desktop"
    os.environ["DATA_DIR"] = data_dir
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["LOG_FILE_PATH"] = os.path.join(log_dir, "app.log")
    os.environ["LOG_TO_FILE"] = "true"
    os.environ["UPLOAD_DIR"] = os.path.join(data_dir, "uploads")
    os.environ["FRONTEND_DIST_DIR"] = dist_dir
    os.environ["API_HOST"] = "127.0.0.1"
    os.environ["API_PORT"] = str(port)

    # --- Start uvicorn in a daemon thread -------------------------------
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        timeout_graceful_shutdown=2,
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    logger.info("Waiting for server to start...")
    if not _wait_for_server(port):
        logger.error("Server failed to start within 30 seconds")
        sys.exit(1)
    logger.info("Server is ready")

    # --- Open native window (blocks until closed) -----------------------
    import webview

    window = webview.create_window(
        APP_NAME,
        url=f"http://127.0.0.1:{port}",
        width=1400,
        height=900,
        min_size=(800, 600),
    )

    def on_closed():
        logger.info("Window closed — shutting down server")
        server.should_exit = True

    window.events.closed += on_closed
    webview.start()

    # Give uvicorn a moment to finish in-flight requests
    server_thread.join(timeout=5)
    logger.info("Goodbye")


if __name__ == "__main__":
    main()
