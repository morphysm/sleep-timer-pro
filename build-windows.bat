@echo off
title Sleep Timer Pro — Builder
echo ============================================
echo  Sleep Timer Pro — Windows 11 EXE Builder
echo ============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install ttkbootstrap pystray Pillow pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Building executable...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "SleepTimerPro" ^
  --collect-all ttkbootstrap ^
  --collect-all PIL ^
  --hidden-import pystray ^
  --hidden-import pystray._win32 ^
  Sleep-timer-windows.py

if errorlevel 1 (
    echo ERROR: Build failed. See output above for details.
    pause
    exit /b 1
)

echo [3/3] Zipping executable...
powershell -Command "Compress-Archive -Force -Path 'dist\SleepTimerPro.exe','HOW-TO-USE.txt' -DestinationPath 'SleepTimerPro.zip'"

echo.
echo ============================================
echo  DONE!
echo  SleepTimerPro.zip is ready to send.
echo  Your friends just unzip and double-click.
echo ============================================
echo.
pause
