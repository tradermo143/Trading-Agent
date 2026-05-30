@echo off
title Trading Agent Launcher
cd /d "%~dp0"

echo.
echo  ================================================
echo    Trading Agent  --  Starting up
echo  ================================================
echo.

:: Full path to ngrok
set "NGROK=C:\Users\Sheddy\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

:: Verify ngrok exists
if not exist "%NGROK%" (
    echo  ERROR: ngrok not found. Please reinstall from https://ngrok.com/download
    pause
    exit /b 1
)

:: Start the trading app in its own window
echo  [1/2] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"

:: Wait for app to be ready
timeout /t 3 /nobreak >nul

:: Start ngrok in its own window
echo  [2/2] Starting ngrok tunnel...
start "ngrok" "%NGROK%" http 5000

echo.
echo  Done! Check the ngrok window for your public URL.
echo  It looks like:  https://abc123.ngrok-free.app
echo.
echo  Open that URL from any browser on any device.
echo  Leave username blank, enter your UI_PASSWORD.
echo.
echo  Press any key here to shut everything down.
pause >nul

taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ngrok" /F >nul 2>&1
