@echo off
title Trading Agent Launcher
cd /d "%~dp0"

echo.
echo  ================================================
echo    Trading Agent  --  Starting up
echo  ================================================
echo.

:: Find ngrok — works on any machine regardless of username or install method
set "NGROK="

:: 1. Try ngrok on PATH (works if installed fresh and terminal restarted)
where ngrok >nul 2>&1
if not errorlevel 1 (
    set "NGROK=ngrok"
)

:: 2. If not on PATH, search WinGet packages folder dynamically
if not defined NGROK (
    for /f "tokens=*" %%i in ('dir /b /s "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok*\ngrok.exe" 2^>nul') do (
        set "NGROK=%%i"
    )
)

:: 3. If still not found, ask user to install it
if not defined NGROK (
    echo  ERROR: ngrok not found.
    echo  Install it by running this in PowerShell:
    echo    winget install ngrok.ngrok
    echo  Then run:
    echo    ngrok config add-authtoken YOUR_TOKEN
    echo  Get your token at: https://dashboard.ngrok.com/auth/your-authtoken
    echo.
    pause
    exit /b 1
)

:: Verify ngrok authtoken is configured
"%NGROK%" config check >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok authtoken not set.
    echo  Run this in PowerShell:
    echo    ngrok config add-authtoken YOUR_TOKEN
    echo  Get your token at: https://dashboard.ngrok.com/auth/your-authtoken
    echo.
    pause
    exit /b 1
)

:: Start the trading app in its own window
echo  [1/2] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"

:: Wait for Flask to start
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
