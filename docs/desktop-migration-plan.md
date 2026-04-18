# BirdWeatherViz3 — Desktop Mode Migration Plan

**Status:** Draft
**Owner:** TBD
**Target:** Desktop as default deployment; Docker remains fully supported
**Platforms:** Windows, macOS, Linux (cross-platform from day one)

---

## 1. Goal

Ship BirdWeatherViz3 as a double-click desktop application that launches a native
window, serves the existing React frontend against the existing FastAPI backend on
`localhost`, persists data in a per-user profile directory, and shuts down cleanly
when the window closes. The Docker / web deployment must continue to work from the
same source tree with zero regressions.

## 2. Non-goals (v1)

- No system tray icon. Close window = exit.
- No code signing / notarization. Unsigned binaries are acceptable for v1.
- No auto-update of the application itself (data sync is a separate feature).
- No per-user authentication inside the desktop app.
- No background workers beyond what already exists.

## 3. Architecture

```
┌────────────────────────────────────────────┐
│ desktop.py (new entrypoint)                │
│  1. Resolve user data dir (platformdirs)   │
│  2. Set BWV_MODE=desktop + DB/LOG paths    │
│  3. Pick free port on 127.0.0.1            │
│  4. Start uvicorn in a daemon thread       │
│  5. Wait for /api/v1/health                │
│  6. webview.create_window(...) [blocking]  │
│  7. On close → signal uvicorn → exit       │
└────────────────────────────────────────────┘
           │ serves
           ▼
┌────────────────────────────────────────────┐
│ FastAPI (existing, one conditional branch) │
│  /api/v1/*   → existing routers            │
│  /*          → StaticFiles(dist, html=True)│
│  CORS middleware skipped in desktop mode   │
└────────────────────────────────────────────┘
           │ reads/writes
           ▼
   <user_data_dir>/BirdWeatherViz3/birdweather.db
```

Desktop mode and web mode differ only in:

- Where the SQLite DB lives (user profile vs. `./data/db/`).
- Whether CORS middleware is installed.
- Whether FastAPI mounts the built `frontend/dist/` as static files.
- Whether the frontend auto-syncs on launch (configurable via a persisted setting).

All other behavior is identical.

## 4. Key findings from the code audit

1. **`frontend/src/api/client.ts`** already uses a relative API base URL
   (`VITE_API_BASE_URL || '/api/v1'`), so the same built `dist/` works whether
   FastAPI serves it at `localhost:<random>` or nginx serves it in Docker. No
   frontend source changes needed for the mode switch.
2. **No backend auto-update loop exists.** `AUTO_UPDATE_ENABLED` is defined in
   `backend/app/config.py` and reported by `/api/v1/health`, but nothing reads
   it. The "auto-sync on app load" behavior today actually lives in
   `frontend/src/components/layout/Layout.tsx` lines 26–70, which calls
   `stationsApi.syncAll()` unconditionally on mount.
3. **`CONFIG_PASSWORD` is declared but never enforced.** `verify_config_password()`
   exists in `backend/app/api/deps.py` but no route calls it and no frontend
   component prompts for it. Safe to delete.
4. **No external API keys.** BirdWeather and Open-Meteo are both public endpoints.
5. **`sync-all`** already returns structured per-station results, and
   `Layout.tsx` already owns a sync status banner. Adding a header sync button is
   a UI refactor, not new logic.

## 5. New features folded into this migration

### 5.1 Auto-update-on-start toggle

- Persistent setting stored in the existing settings key-value store.
- Default `true` for desktop installs, `false` for web.
- Consumed by `Layout.tsx` to decide whether to run the existing `autoSync()` effect.
- Exposed in Configuration page as a checkbox.

### 5.2 Shared "Sync All Stations" button

- New component `frontend/src/components/SyncAllButton.tsx`.
- Props: `variant: "header" | "page"`.
- State lifted into new `frontend/src/contexts/SyncContext.tsx` with
  `syncAll()`, `syncing`, `lastResult`, `error`, `lastSyncedAt`.
- Rendered once in the header (via `Layout.tsx`) and once on Configuration page,
  both pointing at the same context so they disable each other during sync.

### 5.3 Drop `CONFIG_PASSWORD`

- Delete `CONFIG_PASSWORD` field from `config.py`.
- Delete `verify_config_password()` from `api/deps.py`.
- Remove from `.env.example`.
- Pure cleanup — no behavior change today.

## 6. Dependencies

Added to a new `backend/requirements-desktop.txt` (kept out of the Docker image):

- `pywebview>=5.0` — native window shell
- `platformdirs>=4.0` — cross-platform user data paths
- `pyinstaller>=6.0` — packaging (dev-only)

Platform-specific notes:

- **Windows**: PyWebView uses Edge WebView2. Preinstalled on Windows 11; Windows 10
  users may need the 2 MB bootstrapper. Detect and prompt on first run.
- **macOS**: PyWebView uses WKWebView. No runtime install needed.
- **Linux**: PyWebView uses WebKitGTK (default) or QtWebEngine. Ship instructions
  for installing `libwebkit2gtk-4.1-0` on Debian/Ubuntu.

## 7. Work breakdown (commit sequence)

Each step is independently verifiable and does not touch the Docker deployment
path until step 3.

1. **Cleanup dead auth code** — delete `CONFIG_PASSWORD`, `verify_config_password`,
   `.env.example` entry, any tests. Pure deletion. (~10 min)
2. **Config additions** — add `MODE`, `FRONTEND_DIST_DIR`, `DATA_DIR` fields to
   `backend/app/config.py`. No behavior change; defaults preserve web mode. (~10 min)
3. **Conditional static mount + app-info endpoint** — in `backend/app/main.py`,
   mount `StaticFiles(dist, html=True)` and skip CORS when `MODE == "desktop"`.
   Add `/api/v1/app-info` returning `{mode, version, data_dir}`. Verified by running
   `BWV_MODE=desktop uvicorn app.main:app` against a pre-built `frontend/dist`. (~20 min)
4. **Persistent `auto_update_on_start` setting** — extend the settings
   repository, add GET/PUT endpoints, seed default based on mode on first run. (~30 min)
5. **Frontend SyncContext + SyncAllButton** — extract shared state into a React
   context, create the button component with header/page variants, wire into
   `Layout.tsx` header and replace the existing button in `Configuration.tsx`.
   Verify both buttons disable each other during sync. (~45 min)
6. **Auto-update-on-start UI** — checkbox in Configuration page bound to the new
   setting, gate `Layout.tsx`'s mount effect on the value. (~20 min)
7. **`backend/app/desktop.py` launcher** — platformdirs-based data dir resolution,
   free-port selection, uvicorn in daemon thread, PyWebView window, clean shutdown
   via `server.should_exit = True`. Launcher logs to `user_log_dir()`. (~60 min)
8. **First-run data migration helper** — if `<user_data_dir>/birdweather.db` does
   not exist but `./data/db/birdweather.db` does, copy it. (~20 min)
9. **PyInstaller specs** — per-OS `.spec` files (or one parameterized spec) that
   bundle `frontend/dist`, hidden imports for FastAPI dynamic routers, and
   platform-specific flags (`--windowed`, `.icns`/`.ico`, `Info.plist` fragments). (~60 min)
10. **GitHub Actions matrix build** — `strategy.matrix.os: [windows-latest,
    macos-latest, ubuntu-latest]` running `npm ci && npm run build` then
    PyInstaller, uploading artifacts named
    `birdweatherviz-{version}-{os}-{arch}.zip`. (~45 min)
11. **Docs** — split README into web + desktop sections, write
    `docs/README-desktop.md` covering install, data locations per OS, reset
    procedure, dev-mode launch. (~20 min)

**Total estimate:** roughly half a day of focused work. Highest risk in steps 7
and 9 (launcher lifecycle + PyInstaller quirks).

## 8. Data locations per platform

Resolved via `platformdirs.user_data_dir("BirdWeatherViz3")`:

| OS      | Path                                               |
|---------|----------------------------------------------------|
| Windows | `%APPDATA%\BirdWeatherViz3\`                       |
| macOS   | `~/Library/Application Support/BirdWeatherViz3/`   |
| Linux   | `~/.local/share/BirdWeatherViz3/`                  |

Subdirectories: `db/`, `logs/`, `uploads/`.

## 9. Risks and open questions

1. **WebView2 on Windows 10** — a small fraction of users won't have it. PyWebView
   can detect and prompt; we'll show a friendly error with a download link.
2. **Uvicorn shutdown on Windows** — `server.should_exit = True` works but can
   hang if requests are in flight. Mitigated with `timeout_graceful_shutdown=2`.
3. **SQLite threading** — confirm `check_same_thread=False` is already set in
   `backend/app/db/session.py` (Docker needs it too, so it probably is).
4. **Build environment** — PyInstaller is host-OS-specific. GitHub Actions matrix
   handles this, but local dev on one OS can only produce binaries for that OS.
5. **macOS Gatekeeper** — unsigned `.app` bundles require right-click → Open on
   first launch. Document this in `README-desktop.md`.
6. **Bundle size** — expect 90–130 MB. Acceptable for v1.

## 10. Decisions locked in

- Desktop is the default deployment going forward.
- Docker remains fully supported, no regressions allowed.
- `CONFIG_PASSWORD` will be deleted rather than left dormant.
- Auto-update-on-start defaults to **on** for fresh desktop installs.
- The header sync button appears on every page, including Configuration
  (consistency > de-duplication; shared context prevents double-firing).
- Cross-platform from day one: Windows + macOS + Linux.

## 11. Out of scope / future work

- Code signing (Windows Authenticode, macOS notarization).
- Auto-update of the application binary itself.
- System tray / background mode.
- First-run wizard / onboarding UI.
- Packaged installers (MSI, DMG, .deb) — v1 ships zips / tarballs.

---

*Source of truth: `docs/desktop-migration-plan.md` in the repo. Linear issues and
Notion pages linked to this file should not contain conflicting details — edit
here first, then re-sync.*
