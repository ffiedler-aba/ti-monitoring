@echo off
setlocal enabledelayedexpansion

REM TI-Monitoring Service Installation Script (Silent Mode)
REM Erstellt Windows-Dienste für cron.py und app.py mit NSSM
REM Läuft ohne Benutzerinteraktion

echo ========================================
echo TI-Monitoring Service Installation (Silent)
echo ========================================
echo.

REM Aktuelles Verzeichnis als Basis-Pfad
set "BASE_PATH=%~dp0"
set "NSSM_EXE=%BASE_PATH%tools\nssm.exe"

REM Prüfe ob NSSM verfügbar ist
if not exist "%NSSM_EXE%" (
    echo FEHLER: tools\nssm.exe nicht gefunden!
    echo Erwarteter Pfad: %NSSM_EXE%
    echo Bitte führe dieses Skript aus dem portable-build Verzeichnis aus.
    exit /b 1
)

REM Prüfe ob Python venv existiert
if not exist "%BASE_PATH%.venv\Scripts\python.exe" (
    echo FEHLER: .venv\Scripts\python.exe nicht gefunden!
    echo Erwarteter Pfad: %BASE_PATH%.venv\Scripts\python.exe
    echo Bitte führe dieses Skript aus dem portable-build Verzeichnis aus.
    exit /b 1
)

REM Python-Executable Pfad setzen (nach der Prüfung)
set "PYTHON_EXE=%BASE_PATH%.venv\Scripts\python.exe"

REM Prüfe ob requirements.txt existiert und installiere Requirements
if exist "%BASE_PATH%requirements.txt" (
    echo ========================================
    echo Installiere Python Requirements
    echo ========================================
    echo.
    echo Aktualisiere pip...
    "%PYTHON_EXE%" -m pip install --upgrade pip --quiet

    echo Installiere Requirements aus requirements.txt...
    "%PYTHON_EXE%" -m pip install -r "%BASE_PATH%requirements.txt" --quiet

    if !errorlevel! equ 0 (
        echo Requirements erfolgreich installiert.
    ) else (
        echo WARNUNG: Requirements-Installation fehlgeschlagen!
        echo Die Anwendung könnte nicht korrekt funktionieren.
        echo Fortfahren mit der Service-Installation...
    )
) else (
    echo WARNUNG: requirements.txt nicht gefunden!
    echo Überspringe Requirements-Installation.
)

REM Service-Konfiguration
set "CRON_SERVICE=TI-Monitoring-Cron"
set "UI_SERVICE=TI-Monitoring-UI"
set "CRON_SCRIPT=%BASE_PATH%cron.py"
set "UI_SCRIPT=%BASE_PATH%app.py"

echo ========================================
echo Installiere %CRON_SERVICE%
echo ========================================

REM Prüfe ob Service bereits existiert und entferne ihn
"%NSSM_EXE%" status "%CRON_SERVICE%" >nul 2>&1
if !errorlevel! equ 0 (
    echo Service %CRON_SERVICE% existiert bereits. Entferne ihn...
    "%NSSM_EXE%" remove "%CRON_SERVICE%" confirm
)

REM Installiere Cron Service
echo Installiere %CRON_SERVICE%...
"%NSSM_EXE%" install "%CRON_SERVICE%" "%PYTHON_EXE%" "%CRON_SCRIPT%"

REM Service-Pfade explizit auf lokale Pfade setzen
echo Korrigiere Service-Pfade...
"%NSSM_EXE%" set "%CRON_SERVICE%" Application "%PYTHON_EXE%"
"%NSSM_EXE%" set "%CRON_SERVICE%" AppParameters "%CRON_SCRIPT%"

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
    exit /b 1
)

echo.
echo ========================================
echo Installiere %UI_SERVICE%
echo ========================================

REM Prüfe ob Service bereits existiert und entferne ihn
"%NSSM_EXE%" status "%UI_SERVICE%" >nul 2>&1
if !errorlevel! equ 0 (
    echo Service %UI_SERVICE% existiert bereits. Entferne ihn...
    "%NSSM_EXE%" remove "%UI_SERVICE%" confirm
)

REM Installiere UI Service
echo Installiere %UI_SERVICE%...
"%NSSM_EXE%" install "%UI_SERVICE%" "%PYTHON_EXE%" "%UI_SCRIPT%"

REM Service-Pfade explizit auf lokale Pfade setzen
echo Korrigiere Service-Pfade...
"%NSSM_EXE%" set "%UI_SERVICE%" Application "%PYTHON_EXE%"
"%NSSM_EXE%" set "%UI_SERVICE%" AppParameters "%UI_SCRIPT%"

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
    exit /b 1
)

echo.
echo ========================================
echo Starte Dienste
echo ========================================

echo Starte %CRON_SERVICE%...
"%NSSM_EXE%" start "%CRON_SERVICE%"

echo Starte %UI_SERVICE%...
"%NSSM_EXE%" start "%UI_SERVICE%"

echo.
echo Dienste gestartet. Status:
"%NSSM_EXE%" status "%CRON_SERVICE%"
"%NSSM_EXE%" status "%UI_SERVICE%"

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
echo Web-Interface: http://localhost:8050
echo.
echo Logs finden Sie in: %BASE_PATH%logs\
echo.

REM Kurze Pause damit der Benutzer die Ausgabe lesen kann
timeout /t 5 /nobreak >nul

exit /b 0
