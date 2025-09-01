# Installation von TI-Monitoring

Diese Anleitung beschreibt die Installation von TI-Monitoring sowohl für Docker als auch für Python venv.

## Voraussetzungen

### Für Docker-Installation
- Docker
- Docker Compose

### Für Python venv-Installation
- Python 3.9 oder höher
- pip
- python3-venv (Ubuntu/Debian)

## Gemeinsame Vorbereitung

### 1. Repository klonen

```bash
git clone https://github.com/lsr-dev/ti-monitoring.git
cd ti-monitoring
```

### 2. Data-Verzeichnis anlegen

```bash
mkdir data
```

### 3. Konfigurationsdateien einrichten

#### .env Datei konfigurieren

```bash
cp .env.example .env
```

Bearbeiten Sie die `.env` Datei und passen Sie folgende Werte an:
```env
# Password for notification settings page
NOTIFICATION_SETTINGS_PASSWORD=IhrSicheresPasswortHier

# SSL configuration (nur für Docker mit HTTPS)
SSL_DOMAIN=ti-monitoring.example.com
SSL_EMAIL=admin@example.com
```

#### notifications.json konfigurieren

```bash
cp notifications.json.example notifications.json
```

Bearbeiten Sie die `notifications.json` Datei und passen Sie Ihre Benachrichtigungsprofile an:
```json
[
  {
    "name": "Team Complete",
    "type": "whitelist",
    "ci_list": [
      "CI001",
      "CI002",
      "CI003"
    ],
    "apprise_urls": [
      "mailto://user:pass@gmail.com",
      "tgram://bottoken/ChatID"
    ]
  }
]
```

#### config.yaml konfigurieren

```bash
cp config.yaml.example config.yaml
```

Bearbeiten Sie die `config.yaml` Datei und passen Sie folgende Werte an:

```yaml
# Core configuration
core:
  # URL for API (Standard gematik API)
  url: "https://ti-lage.prod.ccs.gematik.solutions/lageapi/v1/tilage/bu/PU"
  
  # Path to hdf5 file for saving the availability data 
  file_name: "data/data.hdf5"
  
  # Home URL for dash app (Ihre Domain)
  home_url: "https://ti-monitoring.example.com"
  
  # Time frame for statistics in web app (Standardwert für Plots)
  stats_delta_hours: 12
  
  # Configuration file for notifications
  notifications_config_file: "notifications.json"
  
  # Cron job intervals (in iterations, where each iteration = 5 minutes)
  cron_intervals:
    # Statistics update interval (default: every 2 iterations = 10 minutes)
    statistics_update_interval: 2
    
    # CI list update interval (default: every 288 iterations = 24 hours)
    ci_list_update_interval: 288
```

**Hinweis:** Der Wert `stats_delta_hours` dient als Standardwert für die Plot-Darstellung. Benutzer können den Zeitraum für jeden Plot individuell über ein Dropdown-Menü anpassen (1 Stunde bis 1 Woche). Der gewählte Zeitraum wird in der URL gespeichert.

#### Cron-Intervalle konfigurieren

Die neuen `cron_intervals` Einstellungen ermöglichen es, die Häufigkeit der automatischen Updates zu konfigurieren:

- **`statistics_update_interval`**: Bestimmt, wie oft die Statistiken für die `/stats` Seite berechnet werden
  - **Standard**: `2` (alle 10 Minuten)
  - **Berechnung**: `2 Iterationen × 5 Minuten = 10 Minuten`
  - **Empfehlung**: Für häufige Updates verwenden Sie `1` (alle 5 Minuten), für weniger häufige Updates `4` (alle 20 Minuten)

- **`ci_list_update_interval`**: Bestimmt, wie oft die Liste der Configuration Items aktualisiert wird
  - **Standard**: `288` (alle 24 Stunden)
  - **Berechnung**: `288 Iterationen × 5 Minuten = 1440 Minuten = 24 Stunden`
  - **Empfehlung**: Normalerweise nicht ändern, da sich die CI-Liste selten ändert

**Beispiele für Anpassungen:**
```yaml
cron_intervals:
  # Statistiken alle 5 Minuten berechnen (häufigere Updates)
  statistics_update_interval: 1
  
  # CI-Liste alle 12 Stunden aktualisieren (häufigere Updates)
  ci_list_update_interval: 144
```

**Performance-Hinweise:**
- Häufigere Statistiken-Updates erhöhen die CPU-Last
- Die Statistiken werden in `data/statistics.json` gecacht für bessere Performance
- Bei vielen CIs (>100) empfiehlt sich ein höherer `statistics_update_interval`
```

## Installation mit Docker (Empfohlen)

### Entwicklungsumgebung (docker-compose-dev.yml)

Die Entwicklungsumgebung ist für lokale Tests und Entwicklung optimiert:

```bash
# Container starten
docker compose -f docker-compose-dev.yml up -d

# Status überprüfen
docker compose -f docker-compose-dev.yml ps

# Logs überprüfen
docker compose -f docker-compose-dev.yml logs ti-monitoring-web
docker compose -f docker-compose-dev.yml logs ti-monitoring-cron

# Zugriff testen
curl http://localhost:8050
```

**Features der Entwicklungsumgebung:**
- ✅ Port 8050 direkt auf localhost gemappt
- ✅ Optimierte Logging-Ausgabe für Cron-Container
- ✅ Einfache Konfiguration ohne HTTPS
- ✅ Ideal für lokale Entwicklung und Tests

### Produktionsumgebung (docker-compose.yml)

Die Produktionsumgebung ist für den Live-Betrieb mit HTTPS optimiert:

#### 1. Vorbereitung

```bash
# SSL-Domain in .env konfigurieren
echo "SSL_DOMAIN=ihre-domain.com" >> .env
echo "SSL_EMAIL=admin@ihre-domain.com" >> .env

# Nginx-Konfiguration vorbereiten
mkdir -p nginx/conf.d
mkdir -p letsencrypt-config
```

#### 2. Container starten

```bash
# Container starten
docker compose up -d

# Status überprüfen
docker compose ps
```

#### 3. HTTPS mit Let's Encrypt einrichten

```bash
# Erste Zertifikate anfordern
./init-letsencrypt.sh

# Zertifikate erneuern (automatisch alle 12 Stunden)
docker compose logs certbot
```

#### 4. Logs überprüfen

```bash
# Web-Container
docker compose logs ti-monitoring-web

# Cron-Container
docker compose logs ti-monitoring-cron

# Nginx
docker compose logs nginx

# Certbot
docker compose logs certbot
```

#### Cron-Logging-System

Das Cron-System verwendet ein professionelles Logging-System mit automatischer Rotation:

**Log-Dateien:**
- **Aktuelle Logs**: `data/cron.log` - Enthält die aktuellen Log-Einträge
- **Archivierte Logs**: `data/cron.log.YYYY-MM-DD` - Täglich rotierte Log-Dateien
- **Automatische Bereinigung**: Logs älter als 7 Tage werden automatisch gelöscht

**Log-Format:**
```
[2025-01-27 10:30:15] === CRON JOB STARTING ===
[2025-01-27 10:30:15] Logging initialized - logs will be written to data/cron.log with daily rotation
[2025-01-27 10:30:16] Configuration loaded successfully. Keys: ['file_name', 'url', ...]
[2025-01-27 10:30:17] === ITERATION 1 ===
[2025-01-27 10:30:17] Running cron job at 2025-01-27 10:30:17
```

**Log-Rotation:**
- **Rotation**: Täglich um Mitternacht
- **Aufbewahrung**: 7 Tage Historie
- **Bereinigung**: Automatisch alle 24 Stunden
- **Encoding**: UTF-8 für korrekte Darstellung

**Logs überprüfen:**
```bash
# Aktuelle Logs anzeigen
tail -f data/cron.log

# Logs der letzten 50 Zeilen
tail -n 50 data/cron.log

# Alle verfügbaren Log-Dateien anzeigen
ls -la data/cron.log*

# Spezifisches Datum anzeigen
cat data/cron.log.2025-01-26
```

#### 5. Zugriff testen

- HTTP: `http://ihre-domain.com` (wird zu HTTPS weitergeleitet)
- HTTPS: `https://ihre-domain.com`

**Features der Produktionsumgebung:**
- ✅ Nginx Reverse Proxy mit HTTPS
- ✅ Automatische Let's Encrypt-Zertifikate
- ✅ Ports 80/443 für HTTP/HTTPS
- ✅ Automatische Zertifikatserneuerung
- ✅ Sichere Produktionskonfiguration

**Hinweis**: Die Produktionsumgebung verwendet bereits die optimierte Konfiguration mit ungepufferter Logging-Ausgabe und direktem Port-Zugriff für Debugging-Zwecke.

### Unterschiede zwischen Dev und Prod

| Feature | Entwicklung | Produktion |
|---------|-------------|------------|
| Ports | 8050 → localhost | 80/443 → Internet |
| HTTPS | Nein | Ja (Let's Encrypt) |
| Nginx | Nein | Ja (Reverse Proxy) |
| Logging | Optimiert | Standard |
| Sicherheit | Lokal | Produktionssicher |

## Installation mit Python venv

### 1. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# oder
.venv\Scripts\activate     # Windows
```

### 2. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. Cron-Job einrichten
Das Skript `cron.py` läuft selbstständig dauerhaft im Hintergrund und ruft alle 5 Minuten neue Daten ab. Es sollte nur **einmal gestartet** werden, nicht alle 5 Minuten neu ausgeführt.

Fügen Sie folgenden Eintrag in Ihre crontab ein:

```bash
crontab -e
```

Eintrag hinzufügen:

```cron
# m h  dom mon dow   command
@reboot cd /path/to/ti-monitoring && source .venv/bin/activate && python cron.py
```

**Wichtig**: Verwenden Sie `@reboot` anstatt `*/5 * * * *`, da das Skript kontinuierlich läuft und nicht alle 5 Minuten neu gestartet werden soll.

Alternativ können Sie das Skript manuell starten:

```bash
cd /path/to/ti-monitoring
source .venv/bin/activate
nohup python cron.py > cron.log 2>&1 &
```

#### Cron-Logging-System (Python venv)

Das Cron-System erstellt automatisch strukturierte Log-Dateien:

**Log-Dateien:**
- **Aktuelle Logs**: `data/cron.log` - Enthält die aktuellen Log-Einträge
- **Archivierte Logs**: `data/cron.log.YYYY-MM-DD` - Täglich rotierte Log-Dateien
- **Automatische Bereinigung**: Logs älter als 7 Tage werden automatisch gelöscht

**Logs überprüfen:**
```bash
# Aktuelle Logs anzeigen
tail -f data/cron.log

# Logs der letzten 50 Zeilen
tail -n 50 data/cron.log

# Alle verfügbaren Log-Dateien anzeigen
ls -la data/cron.log*

# Spezifisches Datum anzeigen
cat data/cron.log.2025-01-26
```

**Hinweis**: Das System erstellt automatisch das `data/` Verzeichnis und konfiguriert das Logging. Keine manuelle Konfiguration erforderlich.

### 4. Web-App starten (optional)

```bash
# Im Hintergrund starten
nohup python app.py > app.log 2>&1 &

# Oder mit Gunicorn (empfohlen für Produktion)
pip install gunicorn
gunicorn --bind 0.0.0.0:8050 --workers 2 app:server
```

### 5. Nginx konfigurieren (optional)

Erstellen Sie eine Nginx-Konfiguration für die Web-App:

```nginx
server {
    listen 80;
    server_name ti-monitoring.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Verifikation der Installation

### 1. Datenbank überprüfen

Nach dem ersten Lauf des Cron-Jobs sollte die Datei `data/data.hdf5` erstellt worden sein:
```bash
ls -la data/
```

### 2. Web-Interface testen

- Öffnen Sie die Web-App in Ihrem Browser
- Überprüfen Sie, ob TI-Komponenten angezeigt werden
- Testen Sie die Benachrichtigungseinstellungen

### 3. Cron-Job überprüfen

```bash
# Für Docker
docker compose logs ti-monitoring-cron --tail=50

# Für Python venv - Cron-Logs überprüfen
tail -f data/cron.log
tail -n 50 data/cron.log

# Alle verfügbaren Log-Dateien anzeigen
ls -la data/cron.log*
```

**Log-Status überprüfen:**
- ✅ Log-Datei `data/cron.log` existiert
- ✅ Tägliche Rotation funktioniert (Logs werden archiviert)
- ✅ Automatische Bereinigung läuft (Logs älter als 7 Tage werden gelöscht)
- ✅ Log-Format ist korrekt mit Zeitstempel

## Fehlerbehebung

### Häufige Probleme

#### Docker-Container startet nicht

```bash
# Logs überprüfen
docker compose logs

# Container neu starten
docker compose down
docker compose up -d
```

#### Berechtigungsprobleme mit data-Verzeichnis

```bash
# Berechtigungen korrigieren
sudo chown -R $USER:$USER data/
chmod 755 data/
```

#### Cron-Job funktioniert nicht

- Überprüfen Sie die crontab-Einträge: `crontab -l`
- Testen Sie das Skript manuell: `python cron.py`
- Überprüfen Sie die Logs

#### Web-App ist nicht erreichbar

- Überprüfen Sie, ob der Port 8050 freigegeben ist
- Testen Sie mit: `curl http://localhost:8050`
- Überprüfen Sie Firewall-Einstellungen

### Logs überprüfen

```bash
# Docker
docker compose logs -f

# Python venv - Web-App
tail -f app.log  # falls mit nohup gestartet

# Python venv - Cron-Job
tail -f data/cron.log
tail -n 100 data/cron.log

# Alle Cron-Log-Dateien anzeigen
ls -la data/cron.log*

# Spezifische Log-Datei anzeigen
cat data/cron.log.2025-01-26
```

**Log-Analyse:**
- **Fehler suchen**: `grep -i error data/cron.log`
- **Warnungen suchen**: `grep -i warning data/cron.log`
- **Letzte Iteration**: `grep "ITERATION" data/cron.log | tail -5`
- **Konfigurationsfehler**: `grep -i config data/cron.log`

## Nächste Schritte

Nach erfolgreicher Installation:

1. **Benachrichtigungen konfigurieren**: Passen Sie `notifications.json` an
2. **Monitoring einrichten**: Überwachen Sie die Logs und Performance
3. **Backup-Strategie**: Planen Sie regelmäßige Backups der `data.hdf5`
4. **Log-Monitoring**: Überwachen Sie die Cron-Logs für Fehler und Performance
5. **Updates**: Halten Sie das System aktuell

### Log-Monitoring einrichten

**Automatische Log-Überwachung:**
```bash
# Log-Monitoring-Skript erstellen
cat > monitor_logs.sh << 'EOF'
#!/bin/bash
# Überwacht Cron-Logs auf Fehler
tail -f data/cron.log | grep --line-buffered -i "error\|warning\|fatal"
EOF

chmod +x monitor_logs.sh
```

**Log-Rotation überprüfen:**
```bash
# Überprüfen Sie, ob die Log-Rotation funktioniert
ls -la data/cron.log*
# Sollte mehrere Dateien zeigen: cron.log, cron.log.2025-01-26, etc.
```

## Support

Bei Problemen:
1. Überprüfen Sie die Logs (`data/cron.log`)
2. Konsultieren Sie die README.md
3. Erstellen Sie ein Issue auf GitHub mit detaillierten Logs

### Log-Informationen für Support

**Wichtige Log-Dateien:**
- `data/cron.log` - Aktuelle Cron-Logs
- `data/cron.log.YYYY-MM-DD` - Archivierte Logs
- `app.log` - Web-App Logs (falls mit nohup gestartet)

**Log-Auszug für Support:**
```bash
# Letzte 100 Zeilen der Cron-Logs
tail -n 100 data/cron.log

# Fehler der letzten 24 Stunden
grep -i "error\|warning\|fatal" data/cron.log

# System-Status
grep "ITERATION" data/cron.log | tail -5
```
