@echo off
chcp 65001 >nul 2>nul
title ISLM - Intelligent Service Level Management
color 0A

echo ================================================
echo   ISLM - Intelligent Service Level Management
echo   Starting all services...
echo ================================================
echo.

:: -- Check Python --
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: -- Check Node --
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ and add to PATH.
    pause
    exit /b 1
)

:: -- Check Ollama --
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Ollama not found on PATH. Chat AI features will not work.
    echo          Install from https://ollama.com and run: ollama pull deepseek-r1:1.5b
    echo.
    goto SKIP_OLLAMA
)

echo [INFO] Checking Ollama model...
ollama list 2>nul | findstr /i "deepseek-r1:1.5b" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Pulling deepseek-r1:1.5b model - this may take a few minutes...
    ollama pull deepseek-r1:1.5b
) else (
    echo [OK] deepseek-r1:1.5b model found.
)

:SKIP_OLLAMA
echo.

:: -- Install Backend Dependencies --
echo [1/5] Installing backend dependencies...
python -m pip install --user -q -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)
echo [OK] Backend dependencies installed.
echo.

:: -- Install Frontend Dependencies --
echo [2/5] Installing frontend dependencies...
cd frontend
if not exist node_modules (
    call npm install --silent
) else (
    echo      node_modules exists - skipping
)
cd ..
echo [OK] Frontend dependencies installed.
echo.

:: -- Seed Database --
echo [3/5] Seeding database...
python -m backend.database.seed
echo.

:: -- Start Backend --
echo [4/5] Starting backend server on port 8000...
start "ISLM Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
echo [OK] Backend started.
echo.

:: -- Start Frontend --
echo [5/5] Starting frontend server on port 5173...
start "ISLM Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"
timeout /t 3 /nobreak >nul
echo [OK] Frontend started.
echo.

:: -- Done --
echo ================================================
echo   All services started!
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo ================================================
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo Press any key to STOP all services...
pause >nul

:: -- Cleanup: kill the server windows --
echo.
echo Stopping services...
taskkill /fi "WINDOWTITLE eq ISLM Backend*" /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq ISLM Frontend*" /f >nul 2>nul
echo Done.
