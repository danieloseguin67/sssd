@echo off
echo ========================================
echo Installing Dependencies
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from python.org
    pause
    exit /b 1
)

echo Installing required Python packages...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 0 (
    echo.
    echo ========================================
    echo Installation complete!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Copy config.example.json to config.json
    echo 2. Update config.json with your SQL Server credentials
    echo 3. Run: python setup.py (to test your configuration)
    echo 4. Run: start_dashboard.bat (to start the dashboard)
    echo.
) else (
    echo.
    echo Error: Installation failed
    echo Please check the error messages above
    echo.
)

pause
