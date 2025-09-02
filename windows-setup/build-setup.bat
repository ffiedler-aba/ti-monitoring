@echo off
REM Build-Skript für TI-Monitoring Windows Setup
REM Kompiliert das InnoSetup-Skript zu einer ausführbaren Setup-Datei

echo ========================================
echo TI-Monitoring Setup Builder
echo ========================================
echo.

REM Prüfe ob InnoSetup installiert ist
set "INNO_SETUP=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_SETUP%" (
    set "INNO_SETUP=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist "%INNO_SETUP%" (
    echo FEHLER: InnoSetup nicht gefunden!
    echo Bitte installieren Sie InnoSetup von: https://jrsoftware.org/isinfo.php
    echo.
    echo Erwartete Pfade:
    echo - C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    echo - C:\Program Files\Inno Setup 6\ISCC.exe
    pause
    exit /b 1
)

echo InnoSetup gefunden: %INNO_SETUP%
echo.

REM Erstelle dist Verzeichnis falls nicht vorhanden
if not exist "dist" mkdir "dist"

REM Kopiere benötigte Dateien
echo Kopiere benötigte Dateien...
copy "..\install-service.cmd" "install-service.cmd" >nul
copy "..\README.md" "README.md" >nul

REM Kompiliere das Setup
echo Kompiliere Setup...
"%INNO_SETUP%" "ti-monitoring-setup.iss"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Setup erfolgreich erstellt!
    echo ========================================
    echo.
    echo Setup-Datei: dist\ti-monitoring-setup.exe
    echo.
    echo Sie können das Setup jetzt verteilen und ausführen.
    echo.
) else (
    echo.
    echo ========================================
    echo FEHLER beim Kompilieren!
    echo ========================================
    echo.
    echo Bitte prüfen Sie die Fehlermeldungen oben.
    echo.
)

pause
