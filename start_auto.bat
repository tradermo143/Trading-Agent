@echo off
::
:: start_auto.bat — Runs by Windows Task Scheduler (no user interaction needed)
:: Starts the Trading Agent app + ngrok tunnel, then emails the URL.
:: The app and ngrok keep running after this script exits.
::
cd /d "%~dp0"

:: Log file for debugging scheduled runs
set "LOG=%~dp0logs\auto_start.log"
if not exist "%~dp0logs" mkdir "%~dp0logs"
echo %DATE% %TIME% — Auto-start triggered >> "%LOG%"

:: ── Find ngrok ────────────────────────────────────────────────────────────────
set "NGROK=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
if not exist "%NGROK%" (
    where ngrok >nul 2>&1
    if not errorlevel 1 ( set "NGROK=ngrok" ) else (
        echo %DATE% %TIME% — ERROR: ngrok not found >> "%LOG%"
        exit /b 1
    )
)

:: Kill any existing instances before starting fresh
taskkill /FI "WINDOWTITLE eq Trading Agent" /F >nul 2>&1
taskkill /IM ngrok.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: ── Start app ─────────────────────────────────────────────────────────────────
echo %DATE% %TIME% — Starting Trading Agent app >> "%LOG%"
start "Trading Agent" cmd /k "cd /d %~dp0 && python ui/app.py"
timeout /t 3 /nobreak >nul

:: ── Start ngrok ───────────────────────────────────────────────────────────────
echo %DATE% %TIME% — Starting ngrok >> "%LOG%"
start /min "ngrok" "%NGROK%" http 5000

:: Wait for ngrok to establish the tunnel
timeout /t 6 /nobreak >nul

:: ── Get URL ───────────────────────────────────────────────────────────────────
for /f "usebackq delims=" %%u in (`powershell -NoProfile -Command ^
    "(Invoke-RestMethod http://localhost:4040/api/tunnels).tunnels | ^
     Where-Object {$_.proto -eq 'https'} | ^
     Select-Object -First 1 -ExpandProperty public_url" 2^>nul`) do set "PUBLIC_URL=%%u"

if not defined PUBLIC_URL (
    echo %DATE% %TIME% — ERROR: Could not get ngrok URL >> "%LOG%"
    exit /b 1
)

echo %DATE% %TIME% — URL: %PUBLIC_URL% >> "%LOG%"

:: ── Send email ────────────────────────────────────────────────────────────────
echo %DATE% %TIME% — Sending email notification >> "%LOG%"
python notify.py "%PUBLIC_URL%" >> "%LOG%" 2>&1

echo %DATE% %TIME% — Done. App is running at %PUBLIC_URL% >> "%LOG%"
:: Script exits here — app and ngrok windows keep running
