# BirdWeatherViz3 Test Script (Windows PowerShell)
# Automated testing script for local development.
# Version: 1.0.0

# Functions
function Print-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host ""
}

function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Cleanup function
function Cleanup {
    Print-Header "Shutting Down"
    Print-Info "Stopping servers..."

    if ($BackendJob) {
        Stop-Job -Job $BackendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $BackendJob -ErrorAction SilentlyContinue
    }

    if ($FrontendJob) {
        Stop-Job -Job $FrontendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $FrontendJob -ErrorAction SilentlyContinue
    }

    # Kill any remaining processes on ports 8000 and 3000
    $processes = Get-NetTCPConnection -LocalPort 8000,3000 -ErrorAction SilentlyContinue |
                 Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($proc in $processes) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    }

    Print-Success "All servers stopped"
}

# Register cleanup on exit
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# Main script
Print-Header "BirdWeatherViz3 Test Script"

# Check dependencies
Print-Header "Checking Dependencies"

try {
    $pythonVersion = python --version 2>&1
    Print-Success "Python is installed: $pythonVersion"
} catch {
    Print-Error "Python is NOT installed"
    exit 1
}

try {
    $nodeVersion = node --version 2>&1
    Print-Success "Node.js is installed: $nodeVersion"
} catch {
    Print-Error "Node.js is NOT installed"
    exit 1
}

try {
    $npmVersion = npm --version 2>&1
    Print-Success "npm is installed: $npmVersion"
} catch {
    Print-Error "npm is NOT installed"
    exit 1
}

# Setup backend
Print-Header "Setting Up Backend"

if (!(Test-Path "backend\.env") -and (Test-Path "backend\.env.example")) {
    Print-Info "Creating .env from .env.example..."
    Copy-Item "backend\.env.example" "backend\.env"
    Print-Success ".env file created"
} elseif (Test-Path "backend\.env") {
    Print-Success ".env file already exists"
}

# Check Python dependencies
Print-Info "Checking Python dependencies..."
$importTest = python -c "import fastapi, sqlalchemy, plotly" 2>&1
if ($LASTEXITCODE -eq 0) {
    Print-Success "Backend dependencies are installed"
} else {
    Print-Warning "Some backend dependencies missing"
    Print-Info "Installing backend dependencies..."
    pip install -r backend\requirements.txt
}

# Setup frontend
Print-Header "Setting Up Frontend"

if (!(Test-Path "frontend\.env") -and (Test-Path "frontend\.env.example")) {
    Print-Info "Creating .env from .env.example..."
    Copy-Item "frontend\.env.example" "frontend\.env"
    Print-Success ".env file created"
} elseif (Test-Path "frontend\.env") {
    Print-Success ".env file already exists"
}

if (!(Test-Path "frontend\node_modules")) {
    Print-Warning "node_modules not found"
    Print-Info "Installing frontend dependencies..."
    Push-Location frontend
    npm install
    Pop-Location
    Print-Success "Frontend dependencies installed"
} else {
    Print-Success "node_modules already exists"
}

# Start backend
Print-Header "Starting Backend Server"

Print-Info "Starting uvicorn on http://localhost:8000..."

$BackendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD\backend
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

Print-Info "Waiting for backend to start..."
Start-Sleep -Seconds 3

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Print-Success "Backend is running at http://localhost:8000"
        Print-Info "API docs available at http://localhost:8000/api/v1/docs"
    }
} catch {
    Print-Error "Backend failed to start"
    Cleanup
    exit 1
}

# Start frontend
Print-Header "Starting Frontend Dev Server"

Print-Info "Starting Vite dev server on http://localhost:3000..."

$FrontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD\frontend
    npm run dev
}

Print-Info "Waiting for frontend to start..."
Start-Sleep -Seconds 5

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Print-Success "Frontend is running at http://localhost:3000"
    }
} catch {
    Print-Warning "Frontend might not be ready yet"
    Print-Info "It may take a few more seconds to compile..."
}

# Open browser
Print-Header "Opening Browser"
Print-Info "Opening http://localhost:3000 in your browser..."
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"

# Keep running
Print-Header "Servers Running"
Print-Success "Backend: http://localhost:8000"
Print-Success "Frontend: http://localhost:3000"
Print-Success "API Docs: http://localhost:8000/api/v1/docs"
Write-Host ""
Print-Warning "Press Ctrl+C to stop all servers"
Write-Host ""

try {
    # Keep the script running
    while ($true) {
        Start-Sleep -Seconds 1

        # Check if jobs are still running
        if ($BackendJob.State -ne "Running") {
            Print-Error "Backend stopped unexpectedly"
            break
        }
        if ($FrontendJob.State -ne "Running") {
            Print-Error "Frontend stopped unexpectedly"
            break
        }
    }
} finally {
    Cleanup
}
