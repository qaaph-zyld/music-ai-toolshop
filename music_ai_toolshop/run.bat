@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install -q -r requirements.txt

echo.
echo Starting Music AI Toolshop UI...
echo Open http://127.0.0.1:5055 in your browser.
echo.

python server.py
pause
