# TI-Monitoring Windows Setup

Dieser Ordner enthält die Dateien für die automatische Windows-Installation von TI-Monitoring.

## Dateien

- `ti-monitoring-setup.iss` - InnoSetup-Skript für die Windows-Installation
- `install-service-silent.cmd` - Stille Service-Installation ohne Benutzerinteraktion
- `README.md` - Diese Dokumentation

## Funktionsweise

Das InnoSetup-Skript (`ti-monitoring-setup.iss`) führt folgende Schritte automatisch aus:

1. **GitHub API-Aufruf** - Lädt die neueste Release-Informationen von GitHub
2. **ZIP-Download** - Lädt die neueste portable ZIP-Datei herunter
3. **Automatische Extraktion** - Extrahiert die Dateien in das gewählte Verzeichnis (Standard: `C:\ti-monitor`)
4. **Service-Installation** - Ruft `install-service-silent.cmd` auf, um die Windows-Services zu installieren

## Installation

### Voraussetzungen

- Windows 10/11 (64-bit)
- Administratorrechte
- Internetverbindung für den Download

### Setup erstellen

1. **InnoSetup installieren** - Download von https://jrsoftware.org/isinfo.php
2. **Setup kompilieren**:
   ```cmd
   # InnoSetup öffnen und ti-monitoring-setup.iss laden
   # Oder über Kommandozeile:
   iscc ti-monitoring-setup.iss
   ```

### Setup ausführen

1. **Setup-Datei ausführen** - `ti-monitoring-setup.exe` als Administrator starten
2. **Installationspfad wählen** - Standard: `C:\ti-monitor`
3. **Automatische Installation** - Das Setup lädt und installiert alles automatisch

## Nach der Installation

Nach erfolgreicher Installation sind folgende Services installiert:

- **TI-Monitoring-Cron** - Überwacht TI-Services
- **TI-Monitoring-UI** - Web-Interface auf Port 8050

### Web-Interface

Öffnen Sie http://localhost:8050 in Ihrem Browser.

### Service-Verwaltung

```cmd
# Service-Status prüfen
nssm status TI-Monitoring-Cron
nssm status TI-Monitoring-UI

# Service starten/stoppen
nssm start TI-Monitoring-Cron
nssm stop TI-Monitoring-Cron

# Service entfernen
nssm remove TI-Monitoring-Cron confirm
```

## Logs

Die Logs finden Sie in:
- `C:\ti-monitor\logs\cron.log` - Cron-Service Logs
- `C:\ti-monitor\logs\ui.log` - UI-Service Logs
- `C:\ti-monitor\logs\cron-error.log` - Cron-Fehler
- `C:\ti-monitor\logs\ui-error.log` - UI-Fehler

## Deinstallation

1. **Services entfernen**:
   ```cmd
   nssm remove TI-Monitoring-Cron confirm
   nssm remove TI-Monitoring-UI confirm
   ```

2. **Verzeichnis löschen** - `C:\ti-monitor` manuell löschen

3. **Setup-Deinstallation** - Über "Programme hinzufügen/entfernen" in Windows

## Fehlerbehebung

### Service startet nicht

1. **Logs prüfen** - Schauen Sie in die Log-Dateien
2. **Python-Pfad prüfen** - Stellen Sie sicher, dass `.venv\Scripts\python.exe` existiert
3. **Requirements prüfen** - Führen Sie `install-service-silent.cmd` manuell aus

### Web-Interface nicht erreichbar

1. **Service-Status prüfen** - `nssm status TI-Monitoring-UI`
2. **Port prüfen** - Stellen Sie sicher, dass Port 8050 frei ist
3. **Firewall prüfen** - Windows-Firewall könnte den Port blockieren

## Entwicklung

### InnoSetup-Skript anpassen

Das Skript `ti-monitoring-setup.iss` kann angepasst werden für:

- Andere Installationspfade
- Zusätzliche Dateien
- Andere GitHub-Repositorys
- Zusätzliche Installationsschritte

### Silent-Installation anpassen

Das Skript `install-service-silent.cmd` kann angepasst werden für:

- Andere Service-Namen
- Zusätzliche Konfiguration
- Andere Log-Pfade
- Zusätzliche Validierungen
