@echo off
title Trading Agent Launcher
cd /d "%~dp0"

echo.
echo  ================================================
echo    Trading Agent  --  Starting up
echo  ================================================
echo.

:: Find ngrok using %LOCALAPPDATA% — works on any machine, any username
set "NGROK=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

:: If not at the WinGet path, try PATH directly
if not exist "%NGROK%" (
    where ngrok >nul 2>&1
    if not errorlevel 1 (
        set "NGROK=ngrok"
    ) else (
        echo  ERROR: ngrok not found.
        echo  Install it:   winget install ngrok.ngrok
        echo  Then run:     ngrok config add-authtoken YOUR_TOKEN
        echo  Get token at: https://dashboard.ngrok.com/auth/your-authtoken
        echo.
        pause
        exit /b 1
    )
)

echo  ngrok found. Checking authtoken...

:: Verify ngrok authtoken is configured
"%NGROK%" config check >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok authtoken not set.
    echo  Run:  ngrok config add-authtoken YOUR_TOKEN
    echo  Get token at: https://dashboard.ngrok.com/auth/your-authtoken
    echo.
    pause
    exit /b 1
)

echo  [1/2] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"

timeout /t 3 /nobreak >nul

echo  [2/2] Starting ngrok tunnel...
start "ngrok" "%NGROK%" http 5000

echo.
echo  Both windows are now running.
echo  Check the ngrok window for your public URL.
echo  It looks like: https://abc123.ngrok-free.app
echo.
echo  Open that URL in any browser. Leave username blank, enter UI_PASSWORD.
echo.
echo  Press any key here to shut everything down.
pause >nul

taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ngrok" /F >nul 2>&1
