@echo off
setlocal enabledelayedexpansion

REM TI-Monitoring Docker Installation Script (Silent Mode)
REM Installiert Docker Desktop und startet TI-Monitoring Container
REM Läuft ohne Benutzerinteraktion

echo ========================================
echo TI-Monitoring Docker Installation (Silent)
echo ========================================
echo.

echo DOCKER LÖSUNG: Container-basierte Installation
echo ========================================
echo.
echo Diese Lösung verwendet Docker Container anstatt Windows Services.
echo Vorteile:
echo - Keine Service-Berechtigungsprobleme
echo - Isolierte Python-Umgebung
echo - Einfache Installation und Wartung
echo - Automatischer Neustart bei Fehlern
echo.

REM Prüfe ob Docker bereits installiert ist
docker --version >nul 2>&1
if !errorlevel! equ 0 (
    echo Docker ist bereits installiert.
    docker --version
    goto :docker_ready
)

echo ========================================
echo Docker Desktop Installation erforderlich
echo ========================================

echo Docker ist nicht installiert.
echo.
echo Für automatische Installation:
echo 1. Hyper-V aktivieren: Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
echo 2. Docker Desktop herunterladen: https://www.docker.com/products/docker-desktop/
echo 3. Docker Desktop installieren und starten
echo 4. Dieses Skript erneut ausführen
echo.
echo Installation abgebrochen - Docker erforderlich.
exit /b 1

:docker_ready

echo ========================================
echo Docker Container Installation
echo ========================================

REM Prüfe ob docker-compose-windows.yml existiert
if not exist "docker-compose-windows.yml" (
    echo FEHLER: docker-compose-windows.yml nicht gefunden!
    echo Bitte führe dieses Skript aus dem TI-Monitoring Verzeichnis aus.
    exit /b 1
)

REM Prüfe ob config.yaml existiert
if not exist "config.yaml" (
    echo WARNUNG: config.yaml nicht gefunden!
    echo Erstelle Standard-Konfiguration...
    if exist "config.yaml.example" (
        copy "config.yaml.example" "config.yaml"
        echo config.yaml aus Beispiel erstellt.
    ) else (
        echo FEHLER: Weder config.yaml noch config.yaml.example gefunden!
        exit /b 1
    )
)

REM Prüfe ob notifications.json existiert
if not exist "notifications.json" (
    echo WARNUNG: notifications.json nicht gefunden!
    echo Erstelle Standard-Konfiguration...
    if exist "notifications.json.example" (
        copy "notifications.json.example" "notifications.json"
        echo notifications.json aus Beispiel erstellt.
    ) else (
        echo FEHLER: Weder notifications.json noch notifications.json.example gefunden!
        exit /b 1
    )
)

echo Konfigurationsdateien gefunden.
echo.

echo ========================================
echo Starte TI-Monitoring Container
echo ========================================

echo Baue Docker Images...
docker-compose -f docker-compose-windows.yml build

if !errorlevel! equ 0 (
    echo Docker Images erfolgreich gebaut.
) else (
    echo FEHLER: Docker Build fehlgeschlagen!
    exit /b 1
)

echo.
echo Starte TI-Monitoring Container...
docker-compose -f docker-compose-windows.yml up -d

if !errorlevel! equ 0 (
    echo TI-Monitoring Container erfolgreich gestartet!
) else (
    echo FEHLER: Container Start fehlgeschlagen!
    exit /b 1
)

echo.
echo ========================================
echo Container Status
echo ========================================

echo Prüfe Container Status...
docker-compose -f docker-compose-windows.yml ps

echo.
echo ========================================
echo Installation abgeschlossen
echo ========================================

echo.
echo TI-Monitoring läuft jetzt in Docker Containern!
echo.
echo Container-Namen:
echo - ti-monitoring-web (Web-Interface)
echo - ti-monitoring-cron (Cron-Jobs)
echo.
echo Nützliche Befehle:
echo - Container Status:    docker-compose -f docker-compose-windows.yml ps
echo - Container stoppen:   docker-compose -f docker-compose-windows.yml down
echo - Container neustarten: docker-compose -f docker-compose-windows.yml restart
echo - Logs anzeigen:       docker-compose -f docker-compose-windows.yml logs
echo - Logs verfolgen:      docker-compose -f docker-compose-windows.yml logs -f
echo.
echo Web-Interface: http://localhost:8050
echo.

echo.
echo ========================================
echo Docker Konfiguration
echo ========================================
echo TI-Monitoring läuft in isolierten Docker Containern.
echo Keine Windows Services erforderlich.
echo Automatischer Neustart bei Fehlern.
echo Einfache Wartung und Updates.
echo.

echo.
echo ========================================
echo Installation abgeschlossen
echo ========================================
