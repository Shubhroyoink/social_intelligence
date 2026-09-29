# PowerShell runner for Social Intelligence React + FastAPI stack
# Usage: .\run_react_app.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Location).Path
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Social Intelligence (React + FastAPI Engine)    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python virtual environment
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[!] Virtual environment not found at .venv\Scripts\python.exe" -ForegroundColor Yellow
    Write-Host "[!] Falling back to system python..." -ForegroundColor Yellow
    $PythonExe = "python"
}

# 2. Check frontend dependencies
$FrontendDir = Join-Path $ProjectRoot "frontend"
$NodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $NodeModules)) {
    Write-Host "[*] Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        npm install
    } finally {
        Pop-Location
    }
}

# 3. Start FastAPI Backend on Port 8000
Write-Host "[*] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
$BackendProcess = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m uvicorn api:app --host 127.0.0.1 --port 8000 --reload" `
    -WorkingDirectory $ProjectRoot `
    -PassThru

# 4. Wait briefly and verify backend is spinning up
Start-Sleep -Seconds 2

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Services:" -ForegroundColor White
Write-Host "   - FastAPI API:   http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   - API Docs:      http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "   - React Web UI:  http://localhost:3000" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Starting Vite React Dev Server... (Press Ctrl+C to stop both)" -ForegroundColor Green

# 5. Run Vite Dev Server in foreground & handle cleanup
try {
    Push-Location $FrontendDir
    npm run dev
} finally {
    Pop-Location
    Write-Host "`n[*] Stopping FastAPI backend (PID: $($BackendProcess.Id))..." -ForegroundColor Yellow
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[✓] All services stopped." -ForegroundColor Green
}
