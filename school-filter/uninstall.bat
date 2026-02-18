@echo off
:: ============================================================
:: School Time Filter — Uninstaller
:: Run as Administrator
:: ============================================================

echo.
echo  =============================================
echo   School Time Filter — Uninstall
echo  =============================================
echo.

net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  ERROR: Must be run as Administrator.
    pause
    exit /b 1
)

set INSTALL_DIR=%ProgramFiles%\SchoolFilter

echo [1/4] Stopping filter process...
taskkill /f /im python.exe /fi "WINDOWTITLE eq filter*" >nul 2>&1
:: Kill any python running filter.py
wmic process where "CommandLine like '%%filter.py%%'" delete >nul 2>&1
echo  Done.

echo.
echo [2/4] Removing scheduled task...
schtasks /delete /tn "SchoolTimeFilter" /f >nul 2>&1
echo  Done.

echo.
echo [3/4] Removing firewall rules...
netsh advfirewall firewall delete rule name="SchoolFilter-BlockExternalDNS" >nul 2>&1
netsh advfirewall firewall delete rule name="SchoolFilter-BlockExternalDNS-TCP" >nul 2>&1
echo  Done.

echo.
echo [4/4] Restoring DNS settings...
powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | ForEach-Object { Set-DnsClientServerAddress -InterfaceAlias $_.Name -ResetServerAddresses }" >nul 2>&1
echo  DNS restored to automatic.

echo.
echo  Removing program files...
icacls "%INSTALL_DIR%" /reset /t >nul 2>&1
rd /s /q "%INSTALL_DIR%" >nul 2>&1
echo  Done.

echo.
echo  =============================================
echo   Uninstall complete. Filter has been removed.
echo  =============================================
echo.
pause
