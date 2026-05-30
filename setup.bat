@echo off
echo.
echo  ================================================
echo   Trading Agent — New Machine Setup
echo  ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Download and install Python 3.11+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo  Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

echo.
echo  Done! Next steps:
echo.
echo  1. Create your .env file  ^(copy .env.example to .env and fill in credentials^)
echo  2. Open config.py and set your account_value
echo  3. Make sure Trader Workstation ^(IBKR^) is running on paper trading mode
echo.
echo  Then run:
echo    python main.py          ^<-- daily scanner
echo    python ui/app.py        ^<-- approval UI
echo.
pause
