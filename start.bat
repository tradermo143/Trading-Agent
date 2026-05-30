@echo off
title Trading Agent
cd /d "%~dp0"

echo.
echo  ================================================
echo    Trading Agent  --  Starting up
echo  ================================================
echo.

:: Reload PATH from registry so newly installed tools (ngrok, python) are found
:: This is needed because double-clicking a .bat doesn't inherit the updated PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UserPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SysPath=%%b"
set "PATH=%SysPath%;%UserPath%"

:: Verify ngrok is available
ngrok version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok not found.
    echo  Please install it from https://ngrok.com/download
    echo  Then run:  ngrok config add-authtoken YOUR_TOKEN
    echo.
    pause
    exit /b 1
)

:: Verify ngrok is configured with an authtoken
ngrok config check >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok authtoken not set.
    echo  Run this once:  ngrok config add-authtoken YOUR_TOKEN
    echo  Get your token at: https://dashboard.ngrok.com/auth/your-authtoken
    echo.
    pause
    exit /b 1
)

:: Start the trading app in a separate window
echo  [1/2] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d "%~dp0" && python ui/app.py"

:: Give the app time to start
timeout /t 6 /nobreak >nul

:: Start ngrok tunnel
echo  [2/2] Opening ngrok tunnel...
echo.
echo  -----------------------------------------------
echo   YOUR PUBLIC URL WILL APPEAR BELOW
echo   Open it from any browser on any device
echo   Leave USERNAME blank, enter your UI_PASSWORD
echo  -----------------------------------------------
echo.
ngrok http 5000

:: When ngrok exits (Ctrl+C), shut down the app window too
echo.
echo  Tunnel closed. Shutting down app...
taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
