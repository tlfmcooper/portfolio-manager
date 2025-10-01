@echo off
REM Portfolio Dashboard Startup Script for Windows

echo.
echo 🚀 Starting Portfolio Dashboard...
echo.

REM Check if Podman is installed
where podman >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Podman is not installed. Please install Podman first.
    exit /b 1
)

REM Check if UV is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ UV is not installed. Please install UV first.
    echo    Run: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    exit /b 1
)

REM Check if Redis container exists
podman ps -a | findstr /C:"redis" >nul
if %errorlevel% equ 0 (
    REM Container exists, check if running
    podman ps | findstr /C:"redis" >nul
    if %errorlevel% equ 0 (
        echo ✅ Redis is already running
    ) else (
        echo 🔄 Starting existing Redis container...
        podman start redis
    )
) else (
    echo 🔄 Creating new Redis container...
    podman run -d --name redis -p 6379:6379 redis:latest
)

REM Verify Redis is running
timeout /t 2 /nobreak >nul
podman exec redis redis-cli ping >nul 2>nul
if %errorlevel% equ 0 (
    echo ✅ Redis is running
) else (
    echo ❌ Redis failed to start
    exit /b 1
)

echo.
echo 📝 To start the backend, run:
echo    uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo 📝 To start the frontend, run in a new terminal:
echo    cd frontend ^&^& npm run dev
echo.
echo 🎉 Redis is ready! Start the backend and frontend to complete the setup.
echo.
pause
