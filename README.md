# BirdWeatherViz3 🐦

**Version:** 1.0.0

Next-generation bird detection visualization application built with FastAPI + React, packaged as a single Docker container with persistent storage.

## Overview

BirdWeatherViz3 is a modern, API-first bird monitoring analytics platform that visualizes and analyzes data from BirdWeather stations. It preserves all 25+ visualization types from the original Streamlit version while providing improved architecture, performance, and maintainability.

## Features

✅ **Multi-Station Support** - Monitor multiple BirdWeather stations simultaneously
✅ **25+ Visualizations** - Comprehensive charts including line charts, rose plots, KDE plots, ridge plots, UpSet plots
✅ **Intelligent Auto-Update** - Automatically fetch new detections with smart backfill (30 days)
✅ **Weather Integration** - Historical and current weather data for all detection days
✅ **Notification System** - Apprise integration supporting 80+ notification services
✅ **Single Docker Container** - Everything packaged in one container with persistent storage
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
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Auth, security, logging
│   │   ├── db/models/      # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── repositories/   # Data access layer
│   │   └── utils/          # Utilities
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
│
├── frontend/                # React application
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components (tabs)
│   │   ├── hooks/          # Custom React hooks
│   │   └── stores/         # State management
│   └── package.json        # Node dependencies
│
├── docker/                  # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── supervisord.conf
│
├── scripts/                 # Utility scripts
│   ├── init_db.py
│   └── migrate_v1_data.py
│
├── notes/                   # Old Streamlit app (excluded from git)
└── .gitignore
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

### Option 2: Docker (Production)

```bash
# Build the image
docker build -f docker/Dockerfile -t birdweatherviz3:latest .

# Run the container
docker run -d \
  --name birdweatherviz3 \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e CONFIG_PASSWORD=your-secure-password \
  --restart unless-stopped \
  birdweatherviz3:latest

# Access at http://localhost:8080
```

### Option 3: Docker Compose (Development)

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up --build

# Access at http://localhost:8080
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
| `DATABASE_URL` | SQLite database path | `sqlite:///data/db/birdweather.db` |
| `CONFIG_PASSWORD` | Admin password | `changeme` |
| `JWT_SECRET` | JWT token secret | (generate random) |
| `AUTO_UPDATE_ENABLED` | Enable auto-updates | `true` |
| `AUTO_UPDATE_INTERVAL` | Update interval (seconds) | `3600` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Persistent Data

All data is stored in the `/data` volume:

- `/data/db` - SQLite database
- `/data/logs` - Application logs
- `/data/uploads` - CSV uploads

## API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8080/api/docs`
- ReDoc: `http://localhost:8080/api/redoc`

### Key API Endpoints

- **Authentication:** `POST /api/v1/auth/login`
- **Detections:** `GET /api/v1/detections/daily-counts`
- **Species:** `GET /api/v1/species/`
- **Stations:** `GET /api/v1/stations/`
- **Visualizations:** `GET /api/v1/visualizations/*`
- **Export:** `GET /api/v1/export/detections/csv`

## Visualizations

### Tab 1: Daily Detections
- New species this week gallery
- Daily detection trends by station
- Summary statistics

### Tab 2: Species Analysis
- Species diversity trends (7-day MA)
- Cumulative discovery curve

### Tab 3: Species Details
- 24-hour rose plot (circular activity pattern)
- 48-hour KDE plot (midnight continuity)
- Hourly and monthly patterns
- Detection timeline by station

### Tab 4: Species List
- Bird family analysis
- Monthly detection champions
- Detection vs. confidence scatter plot
- Mirrored density curves
- Ridge plot (activity patterns)
- Multi-species bullseye chart
- Top 50 hourly patterns
- Weekly trends bubble chart

### Tab 5: Station Comparison
- Comprehensive station statistics
- UpSet plot (species overlap)
- Per-station breakdowns

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

### Multiple Instances

Run separate instances for different geographic areas:

```bash
# Pittsburgh area
docker run -d --name bw-pgh -p 8081:8080 -v ./data-pgh:/data birdweatherviz3

# New York area
docker run -d --name bw-nyc -p 8082:8080 -v ./data-nyc:/data birdweatherviz3
```

### Backup

```bash
# Backup database
docker exec birdweatherviz3 sqlite3 /data/db/birdweather.db ".backup '/data/backup.db'"

# Copy backup out of container
docker cp birdweatherviz3:/data/backup.db ./backup-$(date +%Y%m%d).db
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs birdweatherviz3

# Check health
docker inspect --format='{{.State.Health.Status}}' birdweatherviz3
```

### Database locked
```bash
# Stop container
docker stop birdweatherviz3

# Check for stale locks
docker run --rm -v $(pwd)/data:/data birdweatherviz3 sqlite3 /data/db/birdweather.db ".databases"

# Restart
docker start birdweatherviz3
```

### Auto-updates not working
1. Check logs: `/data/logs/scheduler.log`
2. Verify station API tokens in Configuration
3. Check `AUTO_UPDATE_ENABLED` environment variable

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Copyright (c) 2025 BirdWeatherViz3

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
