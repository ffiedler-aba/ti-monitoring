@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Docker Desktop Reparatur
echo ========================================
echo.

echo LÖSE DOCKER DAEMON PROBLEME
echo ========================================
echo.

REM Prüfe Docker Version
echo 1. Prüfe Docker Installation...
docker --version
if !errorlevel! neq 0 (
    echo FEHLER: Docker ist nicht installiert!
    echo Bitte installiere Docker Desktop zuerst.
    pause
    exit /b 1
)

echo.
echo 2. Prüfe Docker Daemon Status...
docker info >nul 2>&1
if !errorlevel! equ 0 (
    echo ✓ Docker Daemon läuft korrekt!
    echo.
    echo 3. Teste Docker Funktionalität...
    docker run --rm hello-world >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✓ Docker funktioniert einwandfrei!
        echo.
        echo Docker ist bereit für TI-Monitoring!
        echo Führe jetzt install-docker.cmd aus.
        pause
        exit /b 0
    ) else (
        echo ✗ Docker Test fehlgeschlagen!
        goto :fix_docker
    )
) else (
    echo ✗ Docker Daemon läuft nicht!
    goto :fix_docker
)

:fix_docker
echo.
echo ========================================
echo DOCKER REPARATUR
echo ========================================
echo.

echo Problem: Docker Daemon läuft nicht
echo.
echo LÖSUNGEN:
echo ========================================
echo.
echo 1. DOCKER DESKTOP STARTEN
echo    - Öffne Docker Desktop aus dem Startmenü
echo    - Warte bis "Docker Desktop is running" angezeigt wird
echo.
echo 2. DOCKER DESKTOP NEUSTARTEN
echo    - Rechtsklick auf Docker Desktop Icon in der Taskleiste
echo    - "Restart Docker Desktop" wählen
echo    - Warte bis Neustart abgeschlossen ist
echo.
echo 3. WINDOWS NEUSTARTEN
echo    - Starte Windows neu
echo    - Docker Desktop sollte automatisch starten
echo.
echo 4. HYPER-V PRÜFEN
echo    - PowerShell als Administrator öffnen
echo    - Führe aus: Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V
echo    - Status sollte "Enabled" sein
echo.

set /p "choice=Welche Lösung möchtest du versuchen? (1-4): "

if "!choice!"=="1" (
    echo.
    echo Starte Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo.
    echo Warte 30 Sekunden...
    timeout /t 30 /nobreak >nul
    echo.
    echo Prüfe Docker Daemon erneut...
    docker info >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✓ Docker Daemon läuft jetzt!
        echo Führe install-docker.cmd aus.
    ) else (
        echo ✗ Docker Daemon läuft immer noch nicht.
        echo Versuche Lösung 2 (Neustart).
    )
) else if "!choice!"=="2" (
    echo.
    echo Starte Docker Desktop Neustart...
    echo Bitte starte Docker Desktop manuell neu:
    echo 1. Rechtsklick auf Docker Desktop Icon
    echo 2. "Restart Docker Desktop" wählen
    echo 3. Warte bis Neustart abgeschlossen ist
    echo 4. Starte dieses Skript erneut
    pause
) else if "!choice!"=="3" (
    echo.
    echo Windows Neustart empfohlen.
    echo Starte Windows neu und versuche es erneut.
    pause
) else if "!choice!"=="4" (
    echo.
    echo Prüfe Hyper-V Status...
    powershell -Command "Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V"
    echo.
    echo Falls Hyper-V nicht aktiviert ist:
    echo PowerShell als Administrator öffnen und ausführen:
    echo Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
    echo.
    pause
) else (
    echo Ungültige Auswahl.
    goto :fix_docker
)

echo.
echo ========================================
echo Reparatur abgeschlossen
echo ========================================
echo.
echo Teste Docker erneut mit: docker info
echo Falls erfolgreich: Führe install-docker.cmd aus
echo.
pause
