@echo off
setlocal enabledelayedexpansion

REM TI-Monitoring Docker Installation Script
REM Installiert Docker Desktop und startet TI-Monitoring Container

echo ========================================
echo TI-Monitoring Docker Installation
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
    
    REM Prüfe ob Docker Daemon läuft
    echo Prüfe Docker Daemon Status...
    docker info >nul 2>&1
    if !errorlevel! equ 0 (
        echo Docker Daemon läuft korrekt.
        goto :docker_ready
    ) else (
        echo WARNUNG: Docker Daemon läuft nicht!
        echo.
        echo LÖSUNG: Docker Desktop starten
        echo ========================================
        echo.
        echo 1. Öffne Docker Desktop aus dem Startmenü
        echo 2. Warte bis Docker Desktop vollständig gestartet ist
        echo 3. Starte dieses Skript erneut
        echo.
        echo Alternative: Docker Desktop neu starten
        echo - Rechtsklick auf Docker Desktop Icon in der Taskleiste
        echo - "Restart Docker Desktop" wählen
        echo.
        set /p "choice=Docker Desktop bereits gestartet? (j/n): "
        if /i "!choice!"=="j" (
            echo Prüfe Docker Daemon erneut...
            docker info >nul 2>&1
            if !errorlevel! equ 0 (
                echo Docker Daemon läuft jetzt!
                goto :docker_ready
            ) else (
                echo Docker Daemon läuft immer noch nicht.
                echo Bitte starte Docker Desktop manuell.
                pause
                exit /b 1
            )
        ) else (
            echo Bitte starte Docker Desktop und versuche es erneut.
            pause
            exit /b 1
        )
    )
)

echo ========================================
echo Docker Desktop Installation
echo ========================================

echo Docker ist nicht installiert. Installation erforderlich.
echo.
echo SCHRITT 1: Hyper-V aktivieren
echo ========================================
echo.
echo Hyper-V muss aktiviert werden für Docker Desktop.
echo Führe folgende Schritte aus:
echo.
echo 1. Öffne PowerShell als Administrator
echo 2. Führe aus: Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
echo 3. Starte den Computer neu
echo.
echo SCHRITT 2: Docker Desktop herunterladen
echo ========================================
echo.
echo 1. Gehe zu: https://www.docker.com/products/docker-desktop/
echo 2. Lade Docker Desktop für Windows herunter
echo 3. Installiere Docker Desktop
echo 4. Starte Docker Desktop
echo.
echo SCHRITT 3: Installation fortsetzen
echo ========================================
echo.
echo Nach der Docker Desktop Installation:
echo 1. Starte dieses Skript erneut
echo 2. Docker wird automatisch erkannt
echo 3. TI-Monitoring Container werden gestartet
echo.

set /p "choice=Ist Docker Desktop bereits installiert? (j/n): "
if /i "!choice!"=="j" (
    echo Prüfe Docker erneut...
    docker --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo Docker ist verfügbar!
        goto :docker_ready
    ) else (
        echo Docker ist noch nicht verfügbar.
        echo Bitte installiere Docker Desktop und starte dieses Skript erneut.
        pause
        exit /b 1
    )
) else (
    echo Bitte installiere Docker Desktop und starte dieses Skript erneut.
    pause
    exit /b 1
)

:docker_ready

echo ========================================
echo Docker Container Installation
echo ========================================

REM Prüfe ob docker-compose-windows.yml existiert
if not exist "docker-compose-windows.yml" (
    echo FEHLER: docker-compose-windows.yml nicht gefunden!
    echo Bitte führe dieses Skript aus dem TI-Monitoring Verzeichnis aus.
    pause
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
        pause
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
        pause
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
    pause
    exit /b 1
)

echo.
echo Starte TI-Monitoring Container...
docker-compose -f docker-compose-windows.yml up -d

if !errorlevel! equ 0 (
    echo TI-Monitoring Container erfolgreich gestartet!
) else (
    echo FEHLER: Container Start fehlgeschlagen!
    pause
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
echo Container-Logs finden Sie mit:
echo docker-compose -f docker-compose-windows.yml logs
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
pause
