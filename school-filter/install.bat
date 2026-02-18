@echo off
:: ============================================================
:: School Time Filter — Installer
:: Run this ONCE on each child's computer (as Administrator)
:: ============================================================

echo.
echo  =============================================
echo   School Time Filter — Installation
echo  =============================================
echo.

:: ── Check for Administrator rights ──────────────────────────
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  ERROR: This installer must be run as Administrator.
    echo  Right-click install.bat and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: ── Check Python ─────────────────────────────────────────────
echo [1/5] Checking for Python...
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo.
    echo  Python is not installed.
    echo  Please download and install Python 3 from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During install, check the box that says
    echo  "Add Python to PATH"
    echo.
    echo  Then run this installer again.
    echo.
    pause
    exit /b 1
)
echo  Python found.

:: ── Install dnslib ───────────────────────────────────────────
echo.
echo [2/5] Installing required Python package (dnslib)...
python -m pip install dnslib --quiet
if %errorlevel% NEQ 0 (
    echo  ERROR: Failed to install dnslib.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)
echo  dnslib installed.

:: ── Copy files to a permanent location ───────────────────────
echo.
echo [3/5] Copying program files...
set INSTALL_DIR=%ProgramFiles%\SchoolFilter
mkdir "%INSTALL_DIR%" 2>nul
copy /Y "%~dp0filter.py"  "%INSTALL_DIR%\filter.py"  >nul
copy /Y "%~dp0config.json" "%INSTALL_DIR%\config.json" >nul

echo  Files copied to: %INSTALL_DIR%

:: ── Create scheduled task (runs at every startup as SYSTEM) ──
echo.
echo [4/5] Setting up auto-start task...

:: Remove old task if it exists
schtasks /delete /tn "SchoolTimeFilter" /f >nul 2>&1

:: Create new task: runs at system startup, as SYSTEM, with highest privileges
schtasks /create ^
  /tn "SchoolTimeFilter" ^
  /tr "python \"%INSTALL_DIR%\filter.py\"" ^
  /sc onstart ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /delay 0000:30 ^
  /f >nul

if %errorlevel% NEQ 0 (
    echo  WARNING: Could not create startup task automatically.
    echo  You may need to start filter.py manually each time.
) else (
    echo  Auto-start task created.
)

:: ── Lock down the SchoolFilter folder so kids can't edit config ──
echo.
echo [5/5] Securing installation...
:: Remove write access for standard (non-admin) users
icacls "%INSTALL_DIR%" /inheritance:d >nul
icacls "%INSTALL_DIR%" /remove:g "Users" >nul
icacls "%INSTALL_DIR%" /grant:r "SYSTEM:(OI)(CI)F" >nul
icacls "%INSTALL_DIR%" /grant:r "Administrators:(OI)(CI)F" >nul
echo  Folder permissions set (only Admins can change config).

:: ── Start the filter right now ────────────────────────────────
echo.
echo  Starting filter now...
start "" /min python "%INSTALL_DIR%\filter.py"
timeout /t 3 >nul

echo.
echo  =============================================
echo   Installation complete!
echo  =============================================
echo.
echo  The filter will now:
echo   - Start automatically every time Windows boots
echo   - Block non-school websites during school hours
echo   - Allow all websites outside of school hours
echo.
echo  To customize allowed websites or school hours:
echo   Edit: %INSTALL_DIR%\config.json
echo   (you must be logged in as Administrator)
echo.
echo  To view blocked site log:
echo   Open: %INSTALL_DIR%\filter.log
echo.
pause
