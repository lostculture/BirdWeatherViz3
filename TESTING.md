# BirdWeatherViz3 Testing Guide

This guide explains how to test the BirdWeatherViz3 application locally using the provided test scripts.

## Prerequisites

Before running the test scripts, ensure you have the following installed:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **npm** (comes with Node.js)

## Quick Start

We've provided three test scripts for different platforms:

### Option 1: Cross-Platform Python Script (Recommended)

```bash
python test.py
```

This script works on Windows, Mac, and Linux. It automatically detects your
platform, creates required data directories, installs dependencies, and starts
both servers.

### Option 2: Linux/Mac Bash Script

```bash
chmod +x test.sh
./test.sh
```

This also works in Git Bash on Windows.

### Option 3: Windows PowerShell Script

```powershell
.\test.ps1
```

## What the Test Scripts Do

The test scripts automatically:

1. ✓ Check if Python, Node.js, and npm are installed
2. ✓ Create `.env` files from `.env.example` if they don't exist
3. ✓ Install Python dependencies (if missing)
4. ✓ Install npm dependencies (if missing)
5. ✓ Start the backend API server on http://localhost:8765
6. ✓ Start the frontend dev server on http://localhost:5173
7. ✓ Open your browser to http://localhost:5173
8. ✓ Keep both servers running until you press Ctrl+C

## Manual Testing (Alternative)

If you prefer to run things manually:

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Or with a virtual environment:

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Create Environment Files

```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

### 4. Create Data Directories

The backend requires these directories for the SQLite database, logs, and uploads:

```bash
mkdir -p backend/data/db backend/data/logs backend/data/uploads
```

### 5. Start Backend (Terminal 1)

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

### 6. Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

### 7. Open Browser

Navigate to: http://localhost:5173

The default ports (8765 / 5173) are deliberately well outside both common
dev defaults (8000 / 3000) and the Docker stack's host ports (8001/3001 for
local, 8002/3004 for public-test) so you can run native dev and Docker side
by side without conflicts. Set `BACKEND_PORT` / `FRONTEND_PORT` env vars
before launching if you need different values.

## What to Expect

### Backend (http://localhost:8765)

- Root endpoint returns API info:
  ```json
  {
    "name": "BirdWeatherViz3",
    "version": "1.0.0",
    "status": "running",
    "docs": "/api/v1/docs"
  }
  ```

- Health check at `/api/v1/health`:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "auto_update_enabled": true
  }
  ```

- Interactive API docs at `/api/v1/docs` (Swagger UI)
- Database auto-created at `backend/data/db/birdweather.db`

### Frontend (http://localhost:5173)

**With No Data (Initial State):**

The app will load successfully but show empty states:

- ✓ Navigation bar with 6 menu items
- ✓ Pages load without errors
- ✓ Statistics cards show 0 values
- ✓ Charts display "No data available" messages

This is **expected behavior** - you haven't added any stations or data yet!

**Pages Available:**

1. **Daily Detections** - Statistics overview and daily trends
2. **Species Analysis** - Diversity trends and discovery curves
3. **Species Details** - Individual species analysis (Phase 5)
4. **Species List** - Family statistics and patterns
5. **Station Comparison** - Multi-station comparison table
6. **Configuration** - Settings and station management (Phase 5)

## Adding Test Data

To see the app with actual data, you need to add a station:

### 1. Get a BirdWeather API Token

- Go to https://app.birdweather.com/
- Log in or create an account
- Navigate to your station settings
- Copy your API token

### 2. Add Station via API

Open the API docs at http://localhost:8765/api/v1/docs

1. Find `POST /api/v1/stations/`
2. Click "Try it out"
3. Enter your station details:
   ```json
   {
     "station_id": "12345",
     "name": "My BirdWeather Station",
     "api_token": "your-token-here",
     "latitude": 40.7128,
     "longitude": -74.0060,
     "active": true
   }
   ```
4. Click "Execute"

### 3. Manually Fetch Data (Coming in Phase 5)

For now, you can test the endpoints manually via the API docs to fetch detections from BirdWeather.

## Troubleshooting

### Port Already in Use

If you get port conflicts:

**Backend (Port 8765):**
```bash
# Find process using port 8765
# Windows
netstat -ano | findstr :8765

# Mac/Linux
lsof -i :8765

# Kill the process (use PID from above)
# Windows
taskkill /PID <PID> /F

# Mac/Linux
kill -9 <PID>
```

**Frontend (Port 5173):**
```bash
# Similar process for port 5173
```

If either port is in use, set `BACKEND_PORT` and `FRONTEND_PORT` to free
values before launching the script — see the example in the script's
port-conflict error message.

### Image Cache / Permission Errors

If you see `PermissionError: [Errno 13] Permission denied: '/app'`, the image cache path
defaults to the Docker container path. Set the `DATA_DIR` environment variable in your
`backend/.env` file:

```
DATA_DIR=./data
```

The test scripts handle this automatically via `.env.example`.

### Import Errors (Python)

```bash
cd backend
pip install --upgrade -r requirements.txt
```

### Module Not Found (Frontend)

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Database Errors

Delete the database and restart:

```bash
rm backend/data/db/birdweather.db
# Restart backend - tables will be auto-created
```

### CORS Errors

Make sure:
- Backend is running on port 8765
- Frontend is running on port 5173
- Check `backend/app/config.py` CORS settings

### Vite 404 Errors

Clear the Vite cache:

```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

## Stopping the Servers

### If Using Test Scripts

Press `Ctrl+C` in the terminal running the test script. It will automatically stop both servers.

### If Running Manually

Press `Ctrl+C` in each terminal window where the servers are running.

## Next Steps

Once you've verified everything works:

1. Add your BirdWeather stations
2. Fetch detection data
3. Explore the visualizations
4. Test the API endpoints
5. Report any issues

## Development Tips

- **Hot Reload**: Both backend and frontend support hot reload - changes will auto-update
- **Logs**: Check terminal output for errors
- **Browser Console**: Press F12 to see frontend errors
- **API Testing**: Use the Swagger UI at `/api/v1/docs` to test endpoints
- **Database Inspection**: Use DB Browser for SQLite to inspect `birdweather.db`

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review terminal/console output for error messages
3. Verify all dependencies are correctly installed
4. Check that ports 8765 and 5173 are available

---

**Version:** 2.2.2
**Last Updated:** 2026-04
