@echo off
title Social Intelligence - React + FastAPI
cd /d "%~dp0"

echo ==========================================================
echo  Starting Social Intelligence (React + FastAPI Engine)
echo ==========================================================

REM 1. Set python path (.venv or system)
set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

REM 2. Start FastAPI Backend in background window
echo [*] Starting FastAPI Backend on http://127.0.0.1:8000...
start "Social Intelligence API" cmd /k "cd /d "%~dp0" && "%PYTHON_EXE%" -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload"

REM 3. Check frontend dependencies
cd /d "%~dp0frontend"
if not exist "node_modules\" (
    echo [*] Installing frontend dependencies...
    call npm install
)

REM 4. Start Vite React Dev Server
echo [*] Starting Vite React Dev Server on http://localhost:3000...
start "" "http://localhost:3000"
call npm run dev
