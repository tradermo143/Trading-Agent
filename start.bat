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

if not exist "%NGROK%" (
    where ngrok >nul 2>&1
    if not errorlevel 1 (
        set "NGROK=ngrok"
    ) else (
        echo  ERROR: ngrok not found.
        echo  Install:  winget install ngrok.ngrok
        echo  Then:     ngrok config add-authtoken YOUR_TOKEN
        pause & exit /b 1
    )
)

"%NGROK%" config check >nul 2>&1
if errorlevel 1 (
    echo  ERROR: ngrok authtoken not set.
    echo  Run:  ngrok config add-authtoken YOUR_TOKEN
    echo  Get token: https://dashboard.ngrok.com/auth/your-authtoken
    pause & exit /b 1
)

:: Start the trading app
echo  [1/3] Starting Trading Agent app...
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"
timeout /t 3 /nobreak >nul

:: Start ngrok in background (minimized so it stays out of the way)
echo  [2/3] Starting ngrok tunnel...
start /min "ngrok" "%NGROK%" http 5000

:: Wait for ngrok to connect and fetch the URL from its local API
echo  [3/3] Getting your public URL...
timeout /t 4 /nobreak >nul

for /f "usebackq delims=" %%u in (`powershell -NoProfile -Command "(Invoke-RestMethod http://localhost:4040/api/tunnels).tunnels | Where-Object {$_.proto -eq 'https'} | Select-Object -First 1 -ExpandProperty public_url" 2^>nul`) do set "PUBLIC_URL=%%u"

echo.
echo  ====================================================
if defined PUBLIC_URL (
    echo   YOUR PUBLIC URL:
    echo.
    echo   %PUBLIC_URL%
    echo.
    echo   Open this in any browser, anywhere in the world.
    echo   Leave username blank, enter your UI_PASSWORD.
) else (
    echo   Could not fetch URL automatically.
    echo   Check the minimised ngrok window in your taskbar.
)
echo  ====================================================
echo.
echo  Press any key to shut everything down when done.
pause >nul

taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ngrok" /F >nul 2>&1
echo  Shut down complete.
