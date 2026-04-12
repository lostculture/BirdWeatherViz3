# BirdWeatherViz3 🐦

**Version:** 1.4.4

Next-generation bird detection visualization application built with FastAPI + React, with Docker deployment and optional public access via Cloudflare Tunnel.

## Overview

BirdWeatherViz3 is a modern, API-first bird monitoring analytics platform that visualizes and analyzes data from BirdWeather stations. It preserves all 25+ visualization types from the original Streamlit version while providing improved architecture, performance, and maintainability.

## Features

✅ **Multi-Station Support** - Monitor multiple BirdWeather stations simultaneously
✅ **25+ Visualizations** - Comprehensive charts including line charts, rose plots, KDE plots, ridge plots, UpSet plots
✅ **Intelligent Auto-Update** - Automatically fetch new detections with smart backfill (30 days)
✅ **Weather Integration** - Historical and current weather data for all detection days
✅ **Notification System** - Apprise integration supporting 80+ notification services
✅ **Password Protection** - JWT authentication with bcrypt password hashing for configuration pages
✅ **Rate Limiting** - Protection against brute force attacks on login endpoints
✅ **Public Deployment** - Optional Cloudflare Tunnel integration for secure public access
✅ **SQLite Database** - Zero configuration, file-based database
✅ **RESTful API** - Clean FastAPI backend with OpenAPI documentation
✅ **Modern Frontend** - React + TypeScript with responsive design
✅ **Export Capabilities** - CSV/JSON export for all data

## Technology Stack

### Backend
- **Framework:** FastAPI 0.109
- **Database:** SQLite + SQLAlchemy 2.0
- **Data Processing:** Pandas, NumPy, SciPy
- **Visualization:** Plotly (data generation)
- **Scheduling:** APScheduler
- **Notifications:** Apprise
- **Authentication:** JWT + bcrypt

### Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite 5
- **Routing:** React Router v6
- **State:** Zustand
- **Charts:** react-plotly.js, D3.js
- **Styling:** Tailwind CSS
- **API Client:** Axios

### Deployment
- **Container:** Docker (multi-stage build)
- **Web Server:** Nginx
- **Process Manager:** Supervisor
- **Volumes:** Persistent /data mount

## Project Structure

```
BirdWeatherViz3/
├── backend/                      # FastAPI application
│   ├── app/
│   │   ├── api/v1/              # API endpoints
│   │   ├── core/                # Rate limiting, security
│   │   ├── db/models/           # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic
│   │   ├── repositories/        # Data access layer
│   │   └── utils/               # Utilities
│   ├── Dockerfile               # Backend container
│   ├── reset_password.py        # Password reset CLI
│   └── requirements.txt         # Python dependencies
│
├── frontend/                     # React application
│   ├── src/
│   │   ├── api/                 # API client + auth
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── hooks/               # Custom React hooks
│   │   └── stores/              # State management
│   ├── Dockerfile               # Frontend container
│   ├── nginx.conf               # Nginx configuration
│   └── package.json             # Node dependencies
│
├── docker-compose.yml            # Local development
├── docker-compose.public.yml     # Public deployment (Cloudflare)
├── docker-compose.public-test.yml # Public testing (with ports)
├── .env.public.example            # Public instance env template
│
└── LICENSE                        # MIT License
```

## Quick Start

**You only need Docker.** No clone, no Python, no Node.js, no Bun.

```bash
# 1. Download the compose file
curl -O https://raw.githubusercontent.com/lostculture/BirdWeatherViz3/master/docker-compose.public-test.yml

# 2. Set the two required secrets
export CONFIG_PASSWORD="pick-a-password"
export JWT_SECRET="$(openssl rand -hex 32)"

# 3. Start (pulls pre-built images automatically)
docker compose -f docker-compose.public-test.yml up -d
```

Then open **http://localhost:3004** (frontend) — the API is at **http://localhost:8002**.

To stop: `docker compose -f docker-compose.public-test.yml down`
To update: `docker compose -f docker-compose.public-test.yml pull && docker compose -f docker-compose.public-test.yml up -d`

Data persists in a Docker named volume across restarts and upgrades. Images are multi-arch (`linux/amd64` + `linux/arm64`), so this works on Intel/AMD Linux, Apple Silicon Macs, and Raspberry Pi 4/5.

---

## Other Install Options

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
- Start uvicorn on :8000 and Vite dev server on :3000
- Open your browser to http://localhost:3000

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
