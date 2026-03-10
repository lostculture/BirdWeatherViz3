# BirdWeatherViz3 🐦

**Version:** 1.3.0

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

### Prerequisites

- **For Docker:** Docker 20.10+
- **For Local Development:** Python 3.11+, Node.js 18+, npm

### Option 1: Automated Test Scripts (Fastest for Testing)

**Recommended for first-time testing!**

We provide automated test scripts that handle all setup:

```bash
# Cross-platform (Python)
python test.py

# Linux/Mac (Bash)
./test.sh

# Windows (PowerShell)
.\test.ps1
```

These scripts automatically:
- ✓ Check dependencies
- ✓ Install requirements
- ✓ Start backend on http://localhost:8000
- ✓ Start frontend on http://localhost:3000
- ✓ Open your browser

**See [TESTING.md](TESTING.md) for detailed testing instructions.**

### Option 2: Docker Compose (Recommended)

```bash
# Set required environment variables
export CONFIG_PASSWORD="your-secure-password"
export JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Start backend and frontend services
docker compose up -d --build

# Access frontend at http://localhost:3001
# Backend API at http://localhost:8001
```

The default `docker-compose.yml` runs:
- **Backend** on port 8001 (FastAPI)
- **Frontend** on port 3001 (Nginx serving React)

### Option 3: Public Deployment with Cloudflare Tunnel

For secure public access without port forwarding:

```bash
# 1. Create .env.public with your secrets
cp .env.public.example .env.public
# Edit .env.public with CONFIG_PASSWORD, JWT_SECRET, CLOUDFLARE_TUNNEL_TOKEN

# 2. Start the public instance
docker compose -p birdweatherviz3-public -f docker-compose.public.yml --env-file .env.public up -d

# No ports exposed - all traffic goes through Cloudflare
```

See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for detailed instructions.

### Running Multiple Instances

You can run both local development and public instances simultaneously:

```bash
# Local development instance
docker compose -p birdweatherviz3-dev up -d

# Public instance (uses separate data volume)
docker compose -p birdweatherviz3-public -f docker-compose.public.yml --env-file .env.public up -d
```

### Option 4: Manual Local Development

For manual setup without the test scripts:

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Set environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000

# API docs available at http://localhost:8000/docs
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env
# Edit .env with API URL

# Start development server
npm run dev

# Access at http://localhost:5173
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
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
```bash
# Format code
npm run format

# Lint
npm run lint
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
