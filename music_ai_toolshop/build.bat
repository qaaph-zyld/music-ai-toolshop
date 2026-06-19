@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo Installing build dependencies...
python -m pip install -q -r build_requirements.txt

echo.
echo Building MusicAIToolshop.exe...
python build_exe.py

echo.
if exist "..\MusicAIToolshop.exe" (
    echo Build complete: ..\MusicAIToolshop.exe
) else (
    echo Build failed.
)
pause
