# BirdWeatherViz3 🐦

**Version:** 2.2.2

Bird detection visualization and analytics platform for [BirdWeather](https://www.birdweather.com) stations. 25+ interactive charts, weather correlation, multi-station support, and automatic data sync.

## Choose Your Install

| | Desktop App | Docker (Server) |
|---|---|---|
| **Best for** | Personal use on your own computer | Always-on server, remote/public access |
| **Install** | Download, extract, double-click | `docker compose up` |
| **Auth** | None needed (localhost only) | Password-protected (JWT + bcrypt) |
| **Data** | OS user data directory | Docker volume |
| **Platforms** | Windows, macOS, Linux | Any Docker host |
| **Get it** | [**Download Desktop**](https://github.com/lostculture/BirdWeatherViz3/releases) | [Docker Quick Start](#docker-quick-start) below |

---

## Desktop App

**No Docker, no Python, no terminal required.** Download, extract, run.

| Platform | Download |
|----------|----------|
| Windows (x64) | [birdweatherviz3-windows-x64.zip](https://github.com/lostculture/BirdWeatherViz3/releases/download/v2.2.2/birdweatherviz3-windows-x64.zip) |
| macOS (Apple Silicon — M1/M2/M3/M4) | [birdweatherviz3-macos-arm64.tar.gz](https://github.com/lostculture/BirdWeatherViz3/releases/download/v2.2.2/birdweatherviz3-macos-arm64.tar.gz) |
| macOS (Intel) | [birdweatherviz3-macos-x64.tar.gz](https://github.com/lostculture/BirdWeatherViz3/releases/download/v2.2.2/birdweatherviz3-macos-x64.tar.gz) |
| Linux (x64) | [birdweatherviz3-linux-x64.tar.gz](https://github.com/lostculture/BirdWeatherViz3/releases/download/v2.2.2/birdweatherviz3-linux-x64.tar.gz) |

1. Download the archive for your OS above
2. Extract it
3. Run `BirdWeatherViz3` (or `./BirdWeatherViz3` on macOS/Linux)

A native window opens with the full dashboard. Everything runs locally on your machine.

**macOS users:** The app is unsigned. Right-click → Open on first launch, or run `xattr -cr BirdWeatherViz3` in Terminal. See the [Desktop App Guide](docs/README-desktop.md) for details.

For first-time setup (adding stations, syncing data), platform notes, and building from source, see the [**Desktop App Guide**](docs/README-desktop.md).

### Updating the desktop app

**Your data is preserved automatically.** The app bundle and your database are stored in different places:

| OS | App location | Database location (preserved across updates) |
|---|---|---|
| Windows | wherever you extracted the zip | `%APPDATA%\BirdWeatherViz3\db\birdweather.db` |
| macOS | wherever you extracted, or `Applications/` | `~/Library/Application Support/BirdWeatherViz3/db/birdweather.db` |
| Linux | wherever you extracted | `~/.local/share/BirdWeatherViz3/db/birdweather.db` |

To update:

1. **(Recommended) Take a backup first.** Open the running app → **Configuration → Database Backup & Restore → Download backup**, save the `.sqlite` file somewhere safe.
2. Quit the app.
3. Delete the old app folder/bundle and replace it with the new release.
4. Launch the new version. It finds the existing database in the OS user data directory and keeps going — no migration step.
5. If anything looks wrong, use **Configuration → Restore from backup** to roll back to the snapshot from step 1.

Schema changes since v2.0.0 (the `taxonomy_translation` and `detection_day_verification` tables) are additive — `create_all()` adds them on first launch and existing rows are untouched.

---

## Docker Quick Start

**For server deployments, always-on monitoring, or public access via Cloudflare Tunnel.**

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) (free). You don't need to install Python, Node.js, or anything else.

**Never used a terminal before? Don't worry — follow these steps exactly and you'll be up and running in about 10 minutes.**

### Step 1 — Install Docker Desktop

Pick the download for your computer:

- **Mac (Apple Silicon — M1/M2/M3/M4):** <https://desktop.docker.com/mac/main/arm64/Docker.dmg>
- **Mac (Intel):** <https://desktop.docker.com/mac/main/amd64/Docker.dmg>
- **Windows 10/11:** <https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe>
- **Linux:** <https://docs.docker.com/desktop/install/linux-install/>

Install and **launch Docker Desktop**. Wait until the whale icon in your menu bar / system tray stops animating — that means Docker is ready.

### Step 2 — Open a Terminal window

You'll paste one block of commands into this window. It looks scary but it's just a place to type instructions.

- **Mac:** Press `⌘ + Space`, type `Terminal`, press Enter.
- **Windows:** Press the Windows key, type `PowerShell`, press Enter.
- **Linux:** Open the app called `Terminal` from your applications menu.

### Step 3 — Paste these commands

Copy the block below for your operating system, paste it into the Terminal, and press Enter. You'll be prompted for an admin password for BirdWeather — pick anything you can remember. The rest is automatic.

<details open>
<summary><b>Mac / Linux</b></summary>

```bash
curl -O https://raw.githubusercontent.com/lostculture/BirdWeatherViz3/master/docker-compose.public-test.yml
mkdir -p bwv3-data
read -s -p "Pick an admin password for BirdWeather: " CONFIG_PASSWORD && echo
export CONFIG_PASSWORD
export JWT_SECRET="$(openssl rand -hex 32)"
export DATA_DIR="$PWD/bwv3-data"
docker compose -f docker-compose.public-test.yml up -d
```
</details>

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/lostculture/BirdWeatherViz3/master/docker-compose.public-test.yml -OutFile docker-compose.public-test.yml
New-Item -ItemType Directory -Force -Path bwv3-data | Out-Null
$pwd_secure = Read-Host -AsSecureString "Pick an admin password for BirdWeather"
$env:CONFIG_PASSWORD = [System.Net.NetworkCredential]::new("", $pwd_secure).Password
$env:JWT_SECRET = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
$env:DATA_DIR = (Resolve-Path bwv3-data).Path
docker compose -f docker-compose.public-test.yml up -d
```
</details>

> **Where does the data live?** The `bwv3-data` folder you just created. It's bind-mounted into the container, so the SQLite database, image cache, logs, and uploads all sit in plain files inside that directory. Back it up by copying it. Move it to a different machine by copying it. A stray `docker compose down -v` or `docker volume prune` can't touch it because it's not in Docker's volume area — it's a regular folder you own.

You'll see some download progress and then messages saying containers are "Started". That means it worked.

### Step 4 — Open it in your browser

Click this link (or copy it into your browser's address bar):

### → <http://localhost:3004>

You'll see the BirdWeather dashboard. Log in with the password you just picked. It will be empty until you add a BirdWeather station in the **Configuration** page.

---

### Stopping, updating, and uninstalling

Back in the same Terminal window, in the same folder. Re-set the same env
vars (`CONFIG_PASSWORD`, `JWT_SECRET`, `DATA_DIR`) before each command if
you've opened a fresh shell, otherwise compose will fail fast.

- **Stop it** (can restart later): `docker compose -f docker-compose.public-test.yml down`
- **Start it again** later: `docker compose -f docker-compose.public-test.yml up -d`
- **Update to the latest version:** `docker compose -f docker-compose.public-test.yml pull` then `up -d` again — your data in `bwv3-data/` is untouched
- **Move to another machine:** copy the entire `bwv3-data/` folder over and run `up -d` on the new host
- **Uninstall:** `docker compose -f docker-compose.public-test.yml down`, then delete the folder you created and the `bwv3-data/` directory

Your data (stations, detection history, settings, taxonomy translations) lives in `bwv3-data/` next to where you ran `up -d`. It's a real folder, not a Docker volume — back it up with `cp -r bwv3-data /somewhere/safe`, or use Configuration → Database Backup & Restore for a single-file SQLite snapshot.

### Troubleshooting

- **"docker: command not found"** — Docker Desktop isn't installed or isn't running. Open the Docker Desktop app and wait for the whale icon to stop animating, then try again.
- **Browser shows "This site can't be reached"** — Give it another 30 seconds, the containers are still starting up. If it still fails, run `docker compose -f docker-compose.public-test.yml logs` and copy the output into a GitHub issue.
- **Something else is using port 3004 or 8002** — Edit `docker-compose.public-test.yml` with any text editor and change the left-hand side of `3004:80` or `8002:8000` to different numbers (e.g. `3999:80`).

---

## Other Install Options

<details>
<summary><b>Desktop app from source</b> (no PyInstaller needed)</summary>

Requires **Python 3.11+** and **[Bun](https://bun.sh)**:

```bash
git clone https://github.com/lostculture/BirdWeatherViz3 && cd BirdWeatherViz3
cd frontend && bun install && bun run build && cd ..
cd backend && pip install -r requirements.txt -r requirements-desktop.txt
python -m app.desktop
```

See [Desktop App Guide](docs/README-desktop.md) for details.
</details>

<details>
<summary><b>Public deployment with Cloudflare Tunnel</b> (no port forwarding)</summary>

```bash
git clone https://github.com/lostculture/BirdWeatherViz3 && cd BirdWeatherViz3
cp .env.public.example .env.public
# Edit .env.public with CONFIG_PASSWORD, JWT_SECRET, CLOUDFLARE_TUNNEL_TOKEN
docker compose -p birdweatherviz3-public -f docker-compose.public.yml --env-file .env.public up -d
```

See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for full setup.
</details>

<details>
<summary><b>Build locally from source with Docker Compose</b></summary>

```bash
git clone https://github.com/lostculture/BirdWeatherViz3 && cd BirdWeatherViz3
export CONFIG_PASSWORD="pick-a-password"
export JWT_SECRET="$(openssl rand -hex 32)"
docker compose up -d --build
# Frontend: http://localhost:3001    Backend: http://localhost:8001
```
</details>

<details>
<summary><b>Local development (contributors)</b></summary>

Requires **Python 3.11+** and **[Bun](https://bun.sh)**. From a fresh clone:

```bash
python3 test.py       # Cross-platform
./test.sh             # Linux / macOS
.\test.ps1            # Windows PowerShell
```

The test scripts:
- Create an isolated Python venv at `backend/.venv` (does not touch system Python)
- Install backend deps into the venv via pip
- Install frontend deps via `bun install --frozen-lockfile`
- Start uvicorn on **:8765** and Vite dev server on **:5173**
- Open your browser to http://localhost:5173

Override the default ports if they clash with something else on your machine:

```bash
BACKEND_PORT=8766 FRONTEND_PORT=5174 ./test.sh
```

See [TESTING.md](TESTING.md) for manual setup steps and troubleshooting.
</details>

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_DIR` | Base data directory (image cache, etc.) | `./data` (local), `/app/data` (Docker) |
| `DATABASE_URL` | SQLite database path | `sqlite:///./data/db/birdweather.db` |
| `CONFIG_PASSWORD` | Initial admin password (used until custom password is set) | Required |
| `JWT_SECRET` | JWT token signing secret (32+ chars recommended) | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry time | `1440` (24 hours) |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3001"]` |
| `AUTO_UPDATE_ENABLED` | Enable auto-updates | `true` |
| `AUTO_UPDATE_INTERVAL` | Update interval (seconds) | `3600` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Authentication

The Configuration page is password-protected. On first access:

1. Enter the `CONFIG_PASSWORD` set in environment variables
2. A JWT token is issued and stored in browser localStorage
3. Optionally change to a custom password (stored as bcrypt hash in database)

**Rate Limiting:**
- Login attempts: 5 per minute
- Password changes: 3 per minute

**Reset Password via CLI:**
```bash
docker exec <container-name> python reset_password.py --reset-to-default
```

### Persistent Data

All data is stored in the `/data` volume:

- `/data/db` - SQLite database
- `/data/logs` - Application logs
- `/data/uploads` - CSV uploads

## API Documentation

Interactive API documentation is available in development mode (`DEBUG=true`):

- Swagger UI: `http://localhost:8001/api/v1/docs`
- ReDoc: `http://localhost:8001/api/v1/redoc`

API docs are disabled in production for security.

### Key API Endpoints

- **Authentication:** `POST /api/v1/auth/login`, `PUT /api/v1/auth/password`
- **Detections:** `GET /api/v1/detections/daily-counts`
- **Species:** `GET /api/v1/species/`
- **Stations:** `GET /api/v1/stations/`, `POST /api/v1/stations/{id}/sync`
- **Settings:** `GET /api/v1/settings/`, `POST /api/v1/settings/ebird-taxonomy`
- **Analytics:** `GET /api/v1/analytics/weather-correlation`
- **Health:** `GET /api/v1/health`

## Visualizations

### Daily Detections
- New species this week gallery
- Daily detection trends by station
- Summary statistics

### Species Analysis
- Species diversity trends (7-day MA)
- Cumulative discovery curve

### Species Details
- 24-hour rose plot (circular activity pattern)
- 48-hour KDE plot (midnight continuity)
- Hourly and monthly patterns
- Detection timeline by station

### Species List
- Bird family analysis
- Monthly detection champions
- Detection vs. confidence scatter plot
- Mirrored density curves
- Ridge plot (activity patterns)
- Multi-species bullseye chart
- Top 50 hourly patterns
- Weekly trends bubble chart

### Station Comparison
- Comprehensive station statistics
- UpSet plot (species overlap)
- Per-station breakdowns

### Advanced Analytics
- Detection patterns by temperature
- Detection patterns by wind speed
- Weather correlation analysis
- Seasonal activity patterns

## Development

### Running Tests

#### Backend Tests
```bash
cd backend
pytest tests/ --cov=app --cov-report=html
```

#### Frontend Tests
```bash
cd frontend
npm run test
npm run coverage
```

### Code Quality

#### Backend
```bash
# Format code
black backend/app

# Lint
flake8 backend/app
pylint backend/app

# Type checking
mypy backend/app
```

#### Frontend

Frontend uses **[Biome](https://biomejs.dev)** for linting + formatting (one tool, zero config sprawl):

```bash
cd frontend
bun run lint            # Check for issues
bun run format          # Auto-format
bun run check           # Lint + format + organize imports, with --write
```

## Migration from V1 (Streamlit)

To migrate data from the old Streamlit version:

```bash
# Export data from V1
python scripts/export_v1_data.py

# Import to V3
python scripts/migrate_v1_data.py --source v1_export.csv
```

Or manually via the Configuration UI:
1. Login to Configuration page
2. Upload CSV export from V1
3. Configure stations with API tokens
4. Trigger initial data fetch

## Deployment

### Data Volumes

Each instance uses a Docker named volume for persistent storage. Data persists across container restarts and rebuilds.

To use a bind mount for easier backup access, override the volume in your own `docker-compose.override.yml`:

```yaml
volumes:
  birdweather-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/your/data
```

### Backup

```bash
# Backup database
docker exec birdweatherviz3-backend-1 sqlite3 /app/data/db/birdweather.db ".backup '/app/data/backup.db'"

# Copy backup from data volume
cp /path/to/data/backup.db ./backup-$(date +%Y%m%d).db
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs birdweatherviz3-backend-1
docker logs birdweatherviz3-frontend-1

# Check health
docker compose ps
```

### Authentication issues
```bash
# Reset password to environment variable default
docker exec birdweatherviz3-backend-1 python reset_password.py --reset-to-default
```

### CORS errors on public instance
Ensure `CORS_ORIGINS` includes your public domain:
```yaml
environment:
  - CORS_ORIGINS=["https://your-domain.com"]
```

### Auto-updates not working
1. Check backend logs: `docker logs birdweatherviz3-backend-1`
2. Verify station API tokens in Configuration
3. Check `AUTO_UPDATE_ENABLED` environment variable

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- **BirdWeather** - Bird detection data API
- **Open-Meteo** - Weather data API
- **Wikimedia Commons** - Bird images
- **eBird** - Taxonomy data
- **Plotly** - Interactive visualizations
- **FastAPI** - Modern Python web framework
- **React** - Frontend UI library

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Built with ❤️ for bird enthusiasts and data visualization lovers**
