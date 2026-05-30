@echo off
title Trading Agent — Launcher
cd /d "%~dp0"

echo.
echo  ================================================
echo    Trading Agent  --  Starting up
echo  ================================================
echo.

:: Full path to ngrok — avoids any PATH issues
set "NGROK=C:\Users\Sheddy\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

:: Verify ngrok exists at that path
if not exist "%NGROK%" (
    echo  ERROR: ngrok not found at expected location.
    echo  Please reinstall from https://ngrok.com/download
    echo.
    pause
    exit /b 1
)

:: Verify ngrok has an authtoken configured
"%NGROK%" config check >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok authtoken not set.
    echo  Run this in PowerShell:  ngrok config add-authtoken YOUR_TOKEN
    echo  Get your token at: https://dashboard.ngrok.com/auth/your-authtoken
    echo.
    pause
    exit /b 1
)

:: Start the trading app in its own window
echo  [1/2] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"

:: Wait for app to be ready
timeout /t 6 /nobreak >nul

:: Start ngrok in its own window — the URL will appear there
echo  [2/2] Starting ngrok tunnel...
echo.
echo  A new window will open showing your public URL.
echo  It looks like:  https://abc123.ngrok-free.app
echo  Open that URL from any browser, on any device.
echo.
start "ngrok — Trading Agent" "%NGROK%" http 5000

echo  Both windows are now running.
echo  Check the ngrok window for your public URL.
echo.
echo  Press any key to shut everything down when done.
pause >nul

:: Shut down both windows
taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ngrok — Trading Agent" /F >nul 2>&1
echo  Shut down complete.
