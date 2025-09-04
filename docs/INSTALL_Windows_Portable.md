# TI-Monitoring - Windows Portable Installation

Diese Anleitung erklärt die Installation und Konfiguration des TI-Monitoring Systems als portable Windows-Anwendung.

## 📋 Voraussetzungen

- **Windows 10/11** (64-bit)
- **Administratorrechte** für Service-Installation
- **Internetverbindung** für API Updates

## 🚀 Schnellstart

### 1. Portable Paket entpacken

1. Laden Sie die neueste `ti-monitoring-portable-YYYYMMDD-HHMMSS.zip` herunter
2. Entpacken Sie die ZIP-Datei in einen gewünschten Ordner (z.B. `C:\ti-monitoring\`)
3. Wechseln Sie in das entpackte Verzeichnis:
   ```cmd
   cd C:\ti-monitoring\
   ```

### 2. Konfiguration anpassen

#### Hauptkonfiguration (`config.yaml`)
```yaml
# Footer configuration
footer:
  home:
    label: "Home"
    link: "https://lukas-schmidt-russnak.de"
    enabled: true
    new_tab: true
  documentation:
    label: "Dokumentation"
    link: "https://github.com/lsr-dev/ti-monitoring"
    enabled: true
    new_tab: true
  privacy:
    label: "Datenschutz"
    link: "https://lukas-schmidt-russnak.de/datenschutz/"
    enabled: true
    new_tab: true
  imprint:
    label: "Impressum"
    link: "https://lukas-schmidt-russnak.de/impressum/"
    enabled: true
    new_tab: true
  copyright:
    text: "© Lukas Schmidt-Russnak"
    enabled: true

# Core configuration
core:
  # URL for API
  url: "https://ti-lage.prod.ccs.gematik.solutions/lageapi/v1/tilage/bu/PU"
  
  # TimescaleDB configuration (primary data storage)
  timescaledb:
    enabled: true
    host: "localhost"
    port: 5432
    dbname: "timonitor"
    user: "timonitor"
    password: "timonitor"
    keep_days: 185
  
  # Home URL for dash app
  # home_url entfernt – Zurück-Links führen fest auf '/'
  
  # Time frame for statistics in web app
  stats_delta_hours: 12
  
  # Configuration file for notifications
  notifications_config_file: "notifications.json"
  
  # Cron job intervals (in iterations, where each iteration = 5 minutes)
  cron_intervals:
    # Statistics update interval (default: every 2 iterations = 10 minutes)
    statistics_update_interval: 2
    
    # CI list update interval (default: every 288 iterations = 24 hours)
    ci_list_update_interval: 288
  
  # Header configuration
  header:
    # Page title
    title: "TI-Monitoring"
    
    # Logo configuration
    logo:
      # Path to logo image
      path: "assets/logo.svg"
      
      # Logo alt text
      alt: "TI-Monitoring Logo"
      
      # Logo height (in pixels)
      height: 50
      
      # Logo width (in pixels)
      width: 50

```

#### Benachrichtigungseinstellungen (`notifications.json`)
```json
[
  {
    "name": "Team Infrastructure",
    "type": "whitelist",
    "ci_list": [
      "CI001",
      "CI002",
      "CI003"
    ],
    "apprise_urls": [
      "mmost://<your-mattermost-server>/<channel>/<token>"
    ]
  },
  {
    "name": "Management",
    "apprise_urls": [
      "mailto://user:pass@company.com?to=management@company.com"
    ],
    "ci_list": [
      "CI004",
      "CI005"
    ],
    "type": "whitelist"
  }
]
```

### 3. Installation als Windows-Service (Empfohlen)

**Als Administrator ausführen:**

```cmd
install-service.cmd
```

Das Skript:
- Installiert `TI-Monitoring-Cron` (API-Update Job)
- Installiert `TI-Monitoring-UI` (Web-Interface)
- Konfiguriert automatischen Start
- Richtet Logging ein

### 4. Manuelle Ausführung (Alternative)

Falls Sie die Anwendung manuell starten möchten:

```cmd
# Virtuelle Umgebung aktivieren
.\.venv\Scripts\Activate.ps1

# Web-Interface starten
python app.py

# In separatem Terminal: Cron-Job starten
python cron.py
```

## 🔧 Service-Management

### Service-Status prüfen
```cmd
# Über Windows Services
services.msc

# Über NSSM
tools\nssm.exe status TI-Monitoring-Cron
tools\nssm.exe status TI-Monitoring-UI
```

### Service steuern
```cmd
# Service starten
tools\nssm.exe start TI-Monitoring-Cron
tools\nssm.exe start TI-Monitoring-UI

# Service stoppen
tools\nssm.exe stop TI-Monitoring-Cron
tools\nssm.exe stop TI-Monitoring-UI

# Service entfernen
tools\nssm.exe remove TI-Monitoring-Cron confirm
tools\nssm.exe remove TI-Monitoring-UI confirm
```

## 📊 Web-Interface

Nach der Installation ist das Web-Interface verfügbar unter:

- **URL**: `http://localhost:8050`
- **Status**: Überwachungsdaten und Statistiken
- **Logs**: Systemprotokolle einsehen
- **Einstellungen**: Benachrichtigungen konfigurieren

## 📁 Verzeichnisstruktur

```
ti-monitoring/
├── app.py                    # Hauptanwendung (Streamlit)
├── cron.py                   # Cron-Job für Überwachung
├── config.yaml              # Hauptkonfiguration
├── notifications.json       # Benachrichtigungseinstellungen
├── install-service.cmd      # Service-Installation
├── .venv/                   # Python virtuelle Umgebung
│   └── Scripts/
│       └── python.exe
├── tools/                   # Hilfsprogramme
│   └── nssm.exe            # Non-Sucking Service Manager
├── data/                    # Daten und Konfiguration
│   ├── statistics.json
│   └── ci_list.json
└── logs/                    # Log-Dateien
    ├── cron.log
    ├── cron-error.log
    ├── ui.log
    └── ui-error.log
```

## 🔍 Troubleshooting

### Service startet nicht

1. **Logs prüfen**:
   ```cmd
   type logs\cron-error.log
   type logs\ui-error.log
   ```

2. **Python-Pfad prüfen**:
   ```cmd
   .venv\Scripts\python.exe --version
   ```

3. **Konfiguration validieren**:
   ```cmd
   .venv\Scripts\python.exe -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

### Web-Interface nicht erreichbar

1. **Port prüfen**: Standard ist 8501
2. **Firewall**: Port 8501 freigeben
3. **Service-Status**: `tools\nssm.exe status TI-Monitoring-UI`

### Cron-Job läuft nicht

1. **Service-Status prüfen**:
   ```cmd
   tools\nssm.exe status TI-Monitoring-Cron
   ```

2. **Manuell testen**:
   ```cmd
   .venv\Scripts\python.exe cron.py
   ```

3. **Logs analysieren**:
   ```cmd
   type logs\cron.log
   ```

## 🔄 Updates

### Portable Build aktualisieren

1. **Services stoppen**:
   ```cmd
   tools\nssm.exe stop TI-Monitoring-Cron
   tools\nssm.exe stop TI-Monitoring-UI
   ```

2. **Daten sichern**:
   ```cmd
   xcopy data\*.* backup\ /E /I
   # TimescaleDB-Backup (falls lokal installiert)
   pg_dump -h localhost -U timonitor timonitor > backup\timonitor_backup.sql
   ```

3. **Neue Version entpacken** und Konfiguration übertragen

4. **Services neu installieren**:
   ```cmd
   install-service.cmd
   ```

## 🛡️ Sicherheit

### Empfohlene Maßnahmen

1. **Firewall konfigurieren**:
   - Nur notwendige Ports freigeben
   - Zugriff auf Web-Interface beschränken

2. **Benutzerrechte**:
   - Services mit eingeschränkten Rechten ausführen
   - Log-Verzeichnis schreibgeschützt für normale Benutzer

3. **Backup-Strategie**:
   - Regelmäßige Sicherung der `data/` Verzeichnisse
   - TimescaleDB-Backup (falls lokal installiert)
   - Konfigurationsdateien versionieren

## 📞 Support

Bei Problemen:

1. **Logs sammeln**: `logs/` Verzeichnis
2. **Konfiguration prüfen**: `config.yaml` und `notifications.json`
3. **Service-Status dokumentieren**: `tools\nssm.exe status <service-name>`

## 📝 Changelog

- **v1.0**: Erste portable Version mit Service-Installation
- Automatische venv-Erstellung
- NSSM-Integration für Windows-Services
- Umfassendes Logging

---

**Hinweis**: Diese portable Version ist für Windows-Systeme optimiert und enthält alle notwendigen Abhängigkeiten. Eine separate Python-Installation ist nicht erforderlich.
