@echo off
title Trading Agent
cd /d "%~dp0"

echo.
echo  ================================================
echo    Trading Agent  --  Starting up
echo  ================================================
echo.

:: Check ngrok is configured
ngrok config check >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok is not configured.
    echo  Run this once to set it up:
    echo    ngrok config add-authtoken YOUR_TOKEN
    echo  Get your token at: https://dashboard.ngrok.com/auth/your-authtoken
    echo.
    pause
    exit /b 1
)

:: Start the trading app in a separate window
echo  [1/2] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"

:: Give the app a few seconds to start
timeout /t 6 /nobreak >nul

:: Start ngrok tunnel and display the public URL
echo  [2/2] Opening ngrok tunnel...
echo.
echo  ------------------------------------------------
echo   Your public URL will appear below.
echo   Copy it and open it in ANY browser, anywhere.
echo  ------------------------------------------------
echo.
ngrok http 5000

:: ngrok exits when you press Ctrl+C — close the app window too
echo.
echo  Tunnel closed. Shutting down...
taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
