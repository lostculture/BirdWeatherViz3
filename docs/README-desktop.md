# BirdWeatherViz3 — Desktop App

A double-click desktop application that runs the full BirdWeatherViz3 stack
(FastAPI + React) in a native window on your machine.

## Quick start

1. Download the latest release for your OS from
   [GitHub Releases](https://github.com/lostculture/BirdWeatherViz3/releases):

   | Platform | File |
   |----------|------|
   | Windows (x64) | `birdweatherviz3-windows-x64.zip` |
   | macOS (Apple Silicon — M1/M2/M3/M4) | `birdweatherviz3-macos-arm64.tar.gz` |
   | macOS (Intel) | `birdweatherviz3-macos-x64.tar.gz` |
   | Linux (x64) | `birdweatherviz3-linux-x64.tar.gz` |

2. Extract the archive.
3. Run `BirdWeatherViz3` (or `BirdWeatherViz3.app` on macOS).

The app opens a native window, starts a local web server on a random port, and
connects to it automatically.  No browser needed — everything runs locally.

## Data locations

All data is stored in your OS-standard user data directory:

| OS      | Path                                                 |
|---------|------------------------------------------------------|
| Windows | `%APPDATA%\BirdWeatherViz3\`                         |
| macOS   | `~/Library/Application Support/BirdWeatherViz3/`     |
| Linux   | `~/.local/share/BirdWeatherViz3/`                    |

Subdirectories:

- `db/` — SQLite database (`birdweather.db`)
- `logs/` — Application and desktop launcher logs
- `uploads/` — Uploaded CSV files

## First-run migration

If you have an existing database from a Docker or web deployment at
`./data/db/birdweather.db`, the desktop app will automatically copy it to the
user data directory on first launch.

## Platform notes

### Windows
- Requires Edge WebView2 runtime (preinstalled on Windows 11; Windows 10 may
  need the [Evergreen Bootstrapper](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)).
- The app is unsigned — Windows SmartScreen may warn on first run.  Click
  "More info" → "Run anyway".

### macOS
- Uses WKWebView (built-in, no extra install).
- The app is unsigned — macOS Gatekeeper will block it on first launch.
  Use one of these methods to open it:

  **Method 1 — Right-click (recommended):**
  1. Right-click (or Control-click) on `BirdWeatherViz3.app`
  2. Select **Open** from the context menu
  3. Click **Open** in the dialog that appears

  **Method 2 — System Settings:**
  1. Try to open the app normally (it will be blocked)
  2. Go to **System Settings → Privacy & Security**
  3. Scroll down to find the message about BirdWeatherViz3
  4. Click **Open Anyway**

  **Method 3 — Terminal (removes quarantine flag):**
  ```
  xattr -cr /path/to/BirdWeatherViz3.app
  ```

  You only need to do this once — macOS remembers your choice after the
  first launch.

### Linux
- Requires WebKitGTK.  On Debian/Ubuntu:
  ```
  sudo apt install libwebkit2gtk-4.1-0
  ```

## Running from source (dev mode)

```bash
# 1. Build the frontend
cd frontend && bun install && bun run build && cd ..

# 2. Install desktop dependencies
cd backend
pip install -r requirements.txt -r requirements-desktop.txt

# 3. Launch
python -m app.desktop
```

## Reset / fresh start

Delete the user data directory (see table above) to start with a clean database.

## Environment variables

The desktop launcher sets these automatically — you normally don't need to
change them:

| Variable           | Default (desktop)                   | Description                     |
|--------------------|-------------------------------------|---------------------------------|
| `BWV_MODE`         | `desktop`                           | Enables static file serving, skips CORS |
| `DATABASE_URL`     | `sqlite:///<data_dir>/db/birdweather.db` | User-data-dir database     |
| `FRONTEND_DIST_DIR`| Auto-detected                       | Path to built frontend          |
| `DATA_DIR`         | `<user_data_dir>`                   | Base data directory             |

## Building binaries locally

```bash
pip install pyinstaller>=6.0
pyinstaller birdweatherviz.spec
```

The output lands in `dist/BirdWeatherViz3/`.  This only builds for your
current OS — cross-compilation isn't supported.  Use the GitHub Actions
workflow for all three platforms.
