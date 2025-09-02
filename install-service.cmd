@echo off
setlocal enabledelayedexpansion

REM TI-Monitoring Service Installation Script
REM Erstellt Windows-Dienste für cron.py und app.py mit NSSM

echo ========================================
echo TI-Monitoring Service Installation
echo ========================================
echo.

REM Prüfe ob NSSM verfügbar ist
if not exist "tools\nssm.exe" (
    echo FEHLER: tools\nssm.exe nicht gefunden!
    echo Bitte führe dieses Skript aus dem portable-build Verzeichnis aus.
    pause
    exit /b 1
)

REM Prüfe ob Python venv existiert
if not exist ".venv\Scripts\python.exe" (
    echo FEHLER: .venv\Scripts\python.exe nicht gefunden!
    echo Bitte führe dieses Skript aus dem portable-build Verzeichnis aus.
    pause
    exit /b 1
)

REM Aktuelles Verzeichnis als Basis-Pfad
set "BASE_PATH=%~dp0"
set "PYTHON_EXE=%BASE_PATH%.venv\Scripts\python.exe"
set "NSSM_EXE=%BASE_PATH%tools\nssm.exe"

echo Basis-Pfad: %BASE_PATH%
echo Python: %PYTHON_EXE%
echo NSSM: %NSSM_EXE%
echo.

REM Service-Konfiguration
set "CRON_SERVICE=TI-Monitoring-Cron"
set "UI_SERVICE=TI-Monitoring-UI"
set "CRON_SCRIPT=%BASE_PATH%cron.py"
set "UI_SCRIPT=%BASE_PATH%app.py"

echo ========================================
echo Installiere %CRON_SERVICE%
echo ========================================

REM Prüfe ob Service bereits existiert
"%NSSM_EXE%" status "%CRON_SERVICE%" >nul 2>&1
if !errorlevel! equ 0 (
    echo Service %CRON_SERVICE% existiert bereits.
    set /p "choice=Service entfernen und neu installieren? (j/n): "
    if /i "!choice!"=="j" (
        echo Entferne bestehenden Service...
        "%NSSM_EXE%" remove "%CRON_SERVICE%" confirm
    ) else (
        echo Überspringe %CRON_SERVICE%
        goto :install_ui
    )
)

REM Installiere Cron Service
echo Installiere %CRON_SERVICE%...
"%NSSM_EXE%" install "%CRON_SERVICE%" "%PYTHON_EXE%" "%CRON_SCRIPT%"

if !errorlevel! equ 0 (
    echo Service %CRON_SERVICE% erfolgreich installiert.
    
    REM Konfiguriere Service
    echo Konfiguriere %CRON_SERVICE%...
    "%NSSM_EXE%" set "%CRON_SERVICE%" DisplayName "TI-Monitoring Cron Job"
    "%NSSM_EXE%" set "%CRON_SERVICE%" Description "TI-Monitoring Cron Job - Überwacht TI-Services"
    "%NSSM_EXE%" set "%CRON_SERVICE%" Start SERVICE_AUTO_START
    "%NSSM_EXE%" set "%CRON_SERVICE%" AppDirectory "%BASE_PATH:~0,-1%"
    "%NSSM_EXE%" set "%CRON_SERVICE%" AppStdout "%BASE_PATH%logs\cron.log"
    "%NSSM_EXE%" set "%CRON_SERVICE%" AppStderr "%BASE_PATH%logs\cron-error.log"
    
    REM Erstelle logs Verzeichnis falls nicht vorhanden
    if not exist "%BASE_PATH%logs" mkdir "%BASE_PATH%logs"
    
    echo %CRON_SERVICE% konfiguriert.
) else (
    echo FEHLER: Installation von %CRON_SERVICE% fehlgeschlagen!
)

:install_ui
echo.
echo ========================================
echo Installiere %UI_SERVICE%
echo ========================================

REM Prüfe ob Service bereits existiert
"%NSSM_EXE%" status "%UI_SERVICE%" >nul 2>&1
if !errorlevel! equ 0 (
    echo Service %UI_SERVICE% existiert bereits.
    set /p "choice=Service entfernen und neu installieren? (j/n): "
    if /i "!choice!"=="j" (
        echo Entferne bestehenden Service...
        "%NSSM_EXE%" remove "%UI_SERVICE%" confirm
    ) else (
        echo Überspringe %UI_SERVICE%
        goto :start_services
    )
)

REM Installiere UI Service
echo Installiere %UI_SERVICE%...
"%NSSM_EXE%" install "%UI_SERVICE%" "%PYTHON_EXE%" "%UI_SCRIPT%"

if !errorlevel! equ 0 (
    echo Service %UI_SERVICE% erfolgreich installiert.
    
    REM Konfiguriere Service
    echo Konfiguriere %UI_SERVICE%...
    "%NSSM_EXE%" set "%UI_SERVICE%" DisplayName "TI-Monitoring Web UI"
    "%NSSM_EXE%" set "%UI_SERVICE%" Description "TI-Monitoring Web Interface - Streamlit Anwendung"
    "%NSSM_EXE%" set "%UI_SERVICE%" Start SERVICE_AUTO_START
    "%NSSM_EXE%" set "%UI_SERVICE%" AppDirectory "%BASE_PATH:~0,-1%"
    "%NSSM_EXE%" set "%UI_SERVICE%" AppStdout "%BASE_PATH%logs\ui.log"
    "%NSSM_EXE%" set "%UI_SERVICE%" AppStderr "%BASE_PATH%logs\ui-error.log"
    
    REM Erstelle logs Verzeichnis falls nicht vorhanden
    if not exist "%BASE_PATH%logs" mkdir "%BASE_PATH%logs"
    
    echo %UI_SERVICE% konfiguriert.
) else (
    echo FEHLER: Installation von %UI_SERVICE% fehlgeschlagen!
)

:start_services
echo.
echo ========================================
echo Starte Dienste
echo ========================================

set /p "choice=Dienste jetzt starten? (j/n): "
if /i "%choice%"=="j" (
    echo Starte %CRON_SERVICE%...
    "%NSSM_EXE%" start "%CRON_SERVICE%"
    
    echo Starte %UI_SERVICE%...
    "%NSSM_EXE%" start "%UI_SERVICE%"
    
    echo.
    echo Dienste gestartet. Status:
    "%NSSM_EXE%" status "%CRON_SERVICE%"
    "%NSSM_EXE%" status "%UI_SERVICE%"
)

echo.
echo ========================================
echo Installation abgeschlossen
echo ========================================
echo.
echo Service-Namen:
echo - %CRON_SERVICE%
echo - %UI_SERVICE%
echo.
echo Nützliche Befehle:
echo - Service starten:   nssm start ^<service-name^>
echo - Service stoppen:   nssm stop ^<service-name^>
echo - Service entfernen: nssm remove ^<service-name^> confirm
echo - Service Status:    nssm status ^<service-name^>
echo.
echo Logs finden Sie in: %BASE_PATH%logs\
echo.
pause
