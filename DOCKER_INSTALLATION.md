# TI-Monitoring Docker Installation

## Übersicht

Diese Docker-basierte Installation löst alle Probleme mit Windows Services und Berechtigungen. TI-Monitoring läuft in isolierten Docker Containern.

## Vorteile der Docker-Lösung

- ✅ **Keine Service-Berechtigungsprobleme** - Container laufen isoliert
- ✅ **Keine Python-Installation erforderlich** - Python ist im Container enthalten
- ✅ **Automatischer Neustart** - Container starten automatisch bei Fehlern
- ✅ **Einfache Wartung** - Ein Befehl für Updates und Neustarts
- ✅ **Isolierte Umgebung** - Keine Konflikte mit anderen Anwendungen

## Voraussetzungen

### 1. Hyper-V aktivieren

```powershell
# PowerShell als Administrator ausführen
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

**Wichtig:** Computer nach der Aktivierung neu starten!

### 2. Docker Desktop installieren

1. Gehe zu: https://www.docker.com/products/docker-desktop/
2. Lade Docker Desktop für Windows herunter
3. Installiere Docker Desktop
4. Starte Docker Desktop

## Installation

### Automatische Installation

```cmd
# Führe das Installationsskript aus
install-docker.cmd
```

### Manuelle Installation

```cmd
# 1. Docker Images bauen
docker-compose -f docker-compose-windows.yml build

# 2. Container starten
docker-compose -f docker-compose-windows.yml up -d

# 3. Status prüfen
docker-compose -f docker-compose-windows.yml ps
```

## Verwaltung

### Container Status prüfen

```cmd
docker-compose -f docker-compose-windows.yml ps
```

### Logs anzeigen

```cmd
# Alle Logs
docker-compose -f docker-compose-windows.yml logs

# Logs verfolgen (live)
docker-compose -f docker-compose-windows.yml logs -f

# Nur Web-Interface Logs
docker-compose -f docker-compose-windows.yml logs ti-monitoring-web

# Nur Cron Logs
docker-compose -f docker-compose-windows.yml logs ti-monitoring-cron
```

### Container neustarten

```cmd
# Alle Container neustarten
docker-compose -f docker-compose-windows.yml restart

# Nur Web-Interface neustarten
docker-compose -f docker-compose-windows.yml restart ti-monitoring-web

# Nur Cron neustarten
docker-compose -f docker-compose-windows.yml restart ti-monitoring-cron
```

### Container stoppen

```cmd
# Alle Container stoppen
docker-compose -f docker-compose-windows.yml down

# Container stoppen aber nicht entfernen
docker-compose -f docker-compose-windows.yml stop
```

## Konfiguration

### Konfigurationsdateien

- `config.yaml` - Hauptkonfiguration
- `notifications.json` - Benachrichtigungseinstellungen

### Daten-Persistierung

- **Daten:** `ti-monitoring-data` Volume
- **Logs:** `ti-monitoring-logs` Volume

### Ports

- **Web-Interface:** http://localhost:8050
- **Container-Port:** 8050

## Troubleshooting

### Container starten nicht

```cmd
# Logs prüfen
docker-compose -f docker-compose-windows.yml logs

# Container Status prüfen
docker-compose -f docker-compose-windows.yml ps
```

### Docker Desktop Probleme

1. Docker Desktop neu starten
2. Hyper-V Status prüfen
3. Windows-Features prüfen

### Port bereits belegt

```cmd
# Prüfe welche Anwendung Port 8050 verwendet
netstat -ano | findstr :8050

# Container mit anderem Port starten
# In docker-compose-windows.yml ändern: "8051:8050"
```

## Updates

### Container aktualisieren

```cmd
# 1. Container stoppen
docker-compose -f docker-compose-windows.yml down

# 2. Neue Images bauen
docker-compose -f docker-compose-windows.yml build --no-cache

# 3. Container starten
docker-compose -f docker-compose-windows.yml up -d
```

## Deinstallation

```cmd
# Container stoppen und entfernen
docker-compose -f docker-compose-windows.yml down

# Volumes entfernen (ACHTUNG: Daten gehen verloren!)
docker volume rm ti-monitoring_ti-monitoring-data
docker volume rm ti-monitoring_ti-monitoring-logs

# Images entfernen
docker rmi ti-monitoring_ti-monitoring-web
docker rmi ti-monitoring_ti-monitoring-cron
```

## Support

Bei Problemen:

1. Logs prüfen: `docker-compose -f docker-compose-windows.yml logs`
2. Container Status: `docker-compose -f docker-compose-windows.yml ps`
3. Docker Desktop Status prüfen
4. Hyper-V Status prüfen
