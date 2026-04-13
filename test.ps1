# BirdWeatherViz3 local dev setup (Windows PowerShell)
# Creates an isolated Python venv at backend\.venv and uses bun for the
# frontend. Does not touch system Python or global npm state.

$ErrorActionPreference = "Stop"

function H   ($m) { Write-Host ""; Write-Host "========================================" -ForegroundColor Blue; Write-Host $m -ForegroundColor Blue; Write-Host "========================================" -ForegroundColor Blue; Write-Host "" }
function OK  ($m) { Write-Host "+ $m" -ForegroundColor Green }
function ER  ($m) { Write-Host "x $m" -ForegroundColor Red }
function IN_ ($m) { Write-Host "> $m" -ForegroundColor Cyan }
function WA  ($m) { Write-Host "! $m" -ForegroundColor Yellow }

# Default ports avoid common clashes (React 3000, FastAPI 8000).
# Override with BACKEND_PORT / FRONTEND_PORT env vars if needed.
if (-not $env:BACKEND_PORT)  { $env:BACKEND_PORT  = "8765" }
if (-not $env:FRONTEND_PORT) { $env:FRONTEND_PORT = "5173" }
$BackendPort  = $env:BACKEND_PORT
$FrontendPort = $env:FRONTEND_PORT

$Script:BackendJob  = $null
$Script:FrontendJob = $null

function Cleanup {
    H "Shutting Down"
    if ($Script:BackendJob)  { Stop-Job -Job $Script:BackendJob  -ErrorAction SilentlyContinue; Remove-Job -Job $Script:BackendJob  -ErrorAction SilentlyContinue }
    if ($Script:FrontendJob) { Stop-Job -Job $Script:FrontendJob -ErrorAction SilentlyContinue; Remove-Job -Job $Script:FrontendJob -ErrorAction SilentlyContinue }
    OK "All servers stopped"
}
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

H "BirdWeatherViz3 Test Script"

H "Checking Dependencies"

try {
    $pyVer = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    $parts = $pyVer.Split('.')
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
        ER "Python 3.11+ required (found $pyVer)"; exit 1
    }
    OK "Python $pyVer"
} catch {
    ER "Python 3.11+ is NOT installed"; exit 1
}

try {
    $bunVer = & bun --version 2>&1
    OK "bun $bunVer"
} catch {
    ER "bun is NOT installed"
    Write-Host "  Install with: powershell -c `"irm bun.sh/install.ps1 | iex`""
    exit 1
}

# ── Backend ──────────────────────────────────────────────────────────────
H "Setting Up Backend"

if (!(Test-Path "backend\.env") -and (Test-Path "backend\.env.example")) {
    Copy-Item "backend\.env.example" "backend\.env"
    OK ".env created from .env.example"
} else {
    OK ".env file already exists"
}

New-Item -ItemType Directory -Force -Path "backend\data\db","backend\data\logs","backend\data\uploads" | Out-Null
OK "Data directories ready"

$VPY = "backend\.venv\Scripts\python.exe"
if (!(Test-Path $VPY)) {
    IN_ "Creating Python venv at backend\.venv ..."
    & python -m venv backend\.venv
    OK "venv created"
} else {
    OK "venv already exists"
}

& $VPY -c "import fastapi, sqlalchemy, plotly" 2>$null
if ($LASTEXITCODE -eq 0) {
    OK "Backend dependencies already installed"
} else {
    IN_ "Installing backend dependencies into venv ..."
    & $VPY -m pip install -q --upgrade pip
    Push-Location backend
    & ..\$VPY -m pip install -q -r requirements.txt
    Pop-Location
    OK "Backend dependencies installed"
}

# ── Frontend ─────────────────────────────────────────────────────────────
H "Setting Up Frontend"

if (!(Test-Path "frontend\.env") -and (Test-Path "frontend\.env.example")) {
    Copy-Item "frontend\.env.example" "frontend\.env"
    OK ".env created from .env.example"
} else {
    OK ".env file already exists"
}

if (!(Test-Path "frontend\node_modules")) {
    IN_ "Installing frontend dependencies with bun ..."
    Push-Location frontend
    & bun install --frozen-lockfile
    Pop-Location
    OK "Frontend dependencies installed"
} else {
    OK "node_modules already exists"
}

# ── Bail if the chosen ports are already bound ───────────────────────────
foreach ($port in @($BackendPort, $FrontendPort)) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        ER "Port $port is already in use."
        Write-Host "  Something else (Docker, another dev server, ...) is bound to it."
        Write-Host "  Either stop that process, or re-run with different ports, e.g.:"
        Write-Host "      `$env:BACKEND_PORT=8766; `$env:FRONTEND_PORT=5174; .\test.ps1"
        exit 1
    }
}

# ── Start backend ────────────────────────────────────────────────────────
H "Starting Backend Server"
IN_ "uvicorn on http://localhost:$BackendPort ..."
$Script:BackendJob = Start-Job -ScriptBlock {
    param($root, $port)
    Set-Location "$root\backend"
    & "$root\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port $port
} -ArgumentList $PWD.Path, $BackendPort

for ($i=0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try { Invoke-WebRequest -Uri "http://localhost:$BackendPort/api/v1/health" -UseBasicParsing -TimeoutSec 3 | Out-Null; break } catch {}
}
try { Invoke-WebRequest -Uri "http://localhost:$BackendPort/api/v1/health" -UseBasicParsing -TimeoutSec 3 | Out-Null; OK "Backend up on http://localhost:$BackendPort" }
catch { ER "Backend failed to start"; Cleanup; exit 1 }

# ── Start frontend ───────────────────────────────────────────────────────
H "Starting Frontend Dev Server"
IN_ "bun run dev on http://localhost:$FrontendPort ..."
$Script:FrontendJob = Start-Job -ScriptBlock {
    param($root, $bp, $fp)
    Set-Location "$root\frontend"
    $env:BACKEND_PORT  = $bp
    $env:FRONTEND_PORT = $fp
    & bun run dev
} -ArgumentList $PWD.Path, $BackendPort, $FrontendPort

for ($i=0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try { Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -UseBasicParsing -TimeoutSec 3 | Out-Null; break } catch {}
}
try { Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -UseBasicParsing -TimeoutSec 3 | Out-Null; OK "Frontend up on http://localhost:$FrontendPort" }
catch { WA "Frontend not ready yet (check job output)" }

H "Opening Browser"
Start-Process "http://localhost:$FrontendPort"

H "Servers Running"
OK "Backend:  http://localhost:$BackendPort"
OK "Frontend: http://localhost:$FrontendPort"
OK "API Docs: http://localhost:$BackendPort/api/v1/docs"
WA "Press Ctrl+C to stop"
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 1
        if ($Script:BackendJob.State  -ne "Running") { ER "Backend stopped unexpectedly";  break }
        if ($Script:FrontendJob.State -ne "Running") { ER "Frontend stopped unexpectedly"; break }
    }
} finally { Cleanup }
