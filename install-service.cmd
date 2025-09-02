@echo off
setlocal enabledelayedexpansion

REM TI-Monitoring Service Installation Script
REM Erstellt Windows-Dienste für cron.py und app.py mit NSSM

echo ========================================
echo TI-Monitoring Service Installation
echo ========================================
echo.

REM Service-Konfiguration
set "USE_LOCAL_SERVICE=true"
set "SERVICE_USER=LocalService"

echo ========================================
echo Konfiguriere Service-Berechtigungen
echo ========================================

echo Verwende LocalService für Services (ohne Passwort erforderlich).
echo Konfiguriere Berechtigungen für LocalService...

REM Setze Berechtigungen für das Installationsverzeichnis für LocalService
echo Setze Berechtigungen für Installationsverzeichnis...
icacls "%BASE_PATH%" /grant "NT AUTHORITY\LOCAL SERVICE":^(OI^)^(CI^)F /T >nul 2>&1
icacls "%BASE_PATH%" /grant "NT AUTHORITY\SYSTEM":^(OI^)^(CI^)F /T >nul 2>&1

echo Berechtigungen für LocalService konfiguriert.
echo.

REM Prüfe ob NSSM verfügbar ist
if not exist "tools\nssm.exe" (
    echo FEHLER: tools\nssm.exe nicht gefunden!
    echo Bitte führe dieses Skript aus dem portable-build Verzeichnis aus.
    pause
    exit /b 1
)

REM Aktuelles Verzeichnis als Basis-Pfad
set "BASE_PATH=%~dp0"

REM Prüfe ob Python venv existiert
if not exist "%BASE_PATH%.venv\Scripts\python.exe" (
    echo FEHLER: .venv\Scripts\python.exe nicht gefunden!
    echo Erwarteter Pfad: %BASE_PATH%.venv\Scripts\python.exe
    echo Bitte führe dieses Skript aus dem portable-build Verzeichnis aus.
    pause
    exit /b 1
)

REM Python-Executable Pfad setzen (nach der Prüfung)
set "PYTHON_EXE=%BASE_PATH%.venv\Scripts\python.exe"

REM Prüfe ob requirements.txt existiert
if not exist "%BASE_PATH%requirements.txt" (
    echo WARNUNG: requirements.txt nicht gefunden!
    echo Erwarteter Pfad: %BASE_PATH%requirements.txt
    echo Überspringe Requirements-Installation.
    goto :skip_requirements
)

REM Installiere/Update Requirements
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
    set /p "choice=Fortfahren trotz Fehler? (j/n): "
    if /i not "!choice!"=="j" (
        echo Installation abgebrochen.
        pause
        exit /b 1
    )
)

:skip_requirements

REM NSSM-Pfad setzen
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

REM WICHTIG: Service-Pfade explizit auf lokale Pfade setzen
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
    
    REM WICHTIG: Service mit LocalService laufen lassen (ohne Passwort)
    echo Konfiguriere Service für LocalService...
    "%NSSM_EXE%" set "%CRON_SERVICE%" ObjectName "LocalService"
    if !errorlevel! equ 0 (
        echo LocalService erfolgreich konfiguriert.
    ) else (
        echo WARNUNG: LocalService Konfiguration fehlgeschlagen.
    )
    
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

REM WICHTIG: Service-Pfade explizit auf lokale Pfade setzen
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
    
    REM WICHTIG: Service mit LocalService laufen lassen (ohne Passwort)
    echo Konfiguriere Service für LocalService...
    "%NSSM_EXE%" set "%UI_SERVICE%" ObjectName "LocalService"
    if !errorlevel! equ 0 (
        echo LocalService erfolgreich konfiguriert.
    ) else (
        echo WARNUNG: LocalService Konfiguration fehlgeschlagen.
    )
    
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
echo Web-Interface: http://localhost:8050
echo.
echo Logs finden Sie in: %BASE_PATH%logs\
echo.

echo.
echo ========================================
echo Service-Konfiguration Information
echo ========================================
echo Service-Kontext: LocalService
echo Services laufen ohne Passwort im LocalService-Kontext.
echo LocalService hat Vollzugriff auf das Installationsverzeichnis.
echo.

echo.
echo ========================================
echo Installation abgeschlossen
echo ========================================
pause
