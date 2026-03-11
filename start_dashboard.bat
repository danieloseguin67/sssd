@echo off
echo ========================================
echo SQL Server Wait Statistics Dashboard
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

REM Check if config.json exists
if not exist config.json (
    echo Error: config.json not found
    echo Please copy config.example.json to config.json and update with your credentials
    pause
    exit /b 1
)

echo Starting dashboard...
echo.
echo Dashboard will be available at: http://127.0.0.1:8050
echo Press Ctrl+C to stop the dashboard
echo.

REM Prevent Dash from trying to use Jupyter integration
set JUPYTER_DASH_DISABLE=1

python sql_wait_stats_dashboard.py
pause
