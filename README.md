# TI-Monitoring

Dieses Tool dient der Überwachung verschiedener Komponenten der Telematikinfrastruktur (TI).

## Vorwort

Dieses Repository entstand aus einem Fork des Originals von Lukas Schmidt-Russnak (https://github.com/lsr-dev/ti-monitoring).

Die ursprüngliche Lösung wurde erheblich erweitert und ist jetzt in einem Zustand, in dem ein Merge in das Original Repository unmöglich ist.

In Absprache mit Lukas Schmidt-Russnak führe ich diesen Fork zukünfig unabhängig weiter. Einzelne Verbesserungen aus dieser erweiterten Version kann ich jedoch bei Bedarf gern in das Originalprojekt einbringen.

### Was unterscheidet dieses Projekt vom Original

- Die App wurde komplett dockerisiert; das ist die einfachste und sicherste Methode, eine komplexe Python-Anwendung mitsamt ihrer Abhängigkeiten zu deployen.
- Umbau der Datenbank auf Postgresql/timescaledb: ermöglicht Retention, komplexe Abfragen und Statistiken, effiziente Speicherung sowie Benutzerprofile.
- Die E-Mail Benachrichtigung der ursprünglichen App wurde ersetzt durch die Integration von [Apprise](https://github.com/caronc/apprise). Vorteile:
  - Einfache Einbindung nahezu beliebiger Benachrichtigungsplattformen, neben SMTP-E-Mail nun auch Slack, Telegram, Teams, Mattermost, verschiedene REST-API Anbieter für E-Mail u.v.a.m.
  - Vollständige [Liste](https://github.com/caronc/apprise?tab=readme-ov-file#supported-notifications) der Benachrichtigungs-Plattformen
  - Dadurch auch Massenversand an viele Abonnenten auf unterschiedlichen Wegen möglich.
- Einfache Benutzeranmeldung mit One-Time-Passwort zur Verwaltung eigener Benachrichtigungsprofile.
- Benachrichtigungs-Konfiguration per UI über eine eigene Webpage.
- Auswahl der zu abonnierenden Topics aus der Liste der *Configuration Items* der gematik API, täglich von `cron.py` aktualisiert.
- Aussehen der Seite konfigurierbar (Logo, viele Texte inkl. der zugehörigen Links im Footer wie Impressum, Datenschutz u.s.w.)
- Design stellenweise überarbeitet und meinen persönlichen Vorstellungen angepasst.
- Der Darstellungs-Zeitraum der Plots ist frei wählbar.
- Ausführliche Statistiken in den Plots der einzelnen Configuration Items und als Gesamtstatistik unter /stats.

### Entwicklungsstand

Bei ti-stats.net handelt es sich um ein in der Freizeit entwickeltes Privatprojekt, das weiter getrieben wird, wenn Zeit dafür übrig ist. Für Hinweise auf Bugs oder Featurewünsche habe ich jederzeit ein offenes Ohr, bitte ausschließlich als [GitHub Issue](https://github.com/elpatron68/ti-monitoring/issues).

### Öffentliche Demo-Instanz

Eine öffentliche Instanz dieser App ist unter https://ti-stats.net/ nutzbar. Sie unterliegt derzeit häufigen Änderungen. Keine Gewährleistung für Funktionalität, Verfügbarkeit und Speicher-Persistenz! Wenn Sie diese App in Ihrem Unternehmen nutzen möchten, sollten Sie sich eine eigene Instanz einrichten.

### Disclaimer

Dieses Projekt wurde teilweise mithilfe von "KI" (Vibe Coding) weiter entwickelt!

## Features

Die Funktionen lassen sich wie folgt zusammenfassen:

* __Abruf und Archivierung__<br>
Die Kernfunktionalität besteht in der regelmäßigen Abfrage des Verfügbarkeitsstatus sämtlicher zentraler TI-Komponenten über eine öffentliche Schnittstelle der gematik GmbH. Die Ergebnisse werden strukturiert in einer TimescaleDB-Datenbank gespeichert. So können auch für längere Beobachtungszeiträume statistische Auswertungen durchgeführt werden, um beispielsweise die Einhaltung von SLAs zu beurteilen.
* __Benachrichtigungen__<br>
Bei Änderungen der Verfügbarkeit können Benachrichtigungen versendet werden. Das System unterstützt nun über 90 verschiedene Benachrichtigungsdienste durch die Integration von Apprise, darunter:
  - E-Mail (über mailto:// URLs)
  - Telegram
  - Slack
  - Discord
  - Microsoft Teams
  - und viele weitere
* __Web-App__<br>
Der aktuelle Status sämtlicher TI-Komponenten lässt sich nach Produkten gruppiert in einer interaktiven Web-App einsehen. Darüber hinaus kann für die einzelnen Komponenten eine Statistik der letzten Stunden aufgerufen werden.

## Installation

Für detaillierte Installationsanweisungen siehe [INSTALL.md](docs/INSTALL.md).

TI-Monitoring kann sowohl mit Docker als auch mit Python *venv* installiert werden. Docker wird für die meisten Anwendungsfälle empfohlen.

### Schnellstart mit Docker

```bash
# Repository klonen
git clone https://github.com/lsr-dev/ti-monitoring.git
cd ti-monitoring

# Konfigurationsdateien einrichten
mkdir data
cp .env.example .env
cp config.yaml.example config.yaml

# Konfigurationsdateien anpassen
nano .env
nano config.yaml

# Container starten
docker compose -f docker-compose-dev.yml up -d
```

### Abhängigkeiten

Das Projekt verwendet eine requirements.txt Datei zur Verwaltung der Abhängigkeiten. Die requirements.txt Datei enthält alle notwendigen Abhängigkeiten, darunter:

- numpy, pandas, psycopg2-binary für Datenverarbeitung
- requests für HTTP-Anfragen
- pytz, tzlocal für Zeitzone-Handling
- dash, plotly für die Webanwendung
- apprise für Benachrichtigungen
- python-dotenv für Umgebungsvariablen-Management
- matplotlib für Beispiele und Entwicklung
- cryptography für Datenverschlüsselung
- psutil, gunicorn, PyYAML

## Konfiguration

Für detaillierte Konfigurationsanweisungen siehe [INSTALL.md](docs/INSTALL.md).

Die Anwendung kann über folgende Konfigurationsdateien konfiguriert werden:

1. **config.yaml** - Hauptkonfigurationsdatei (API-URL, Datenbank, Intervals, etc.)
2. **.env** - Umgebungsvariablen für sensible Daten (Passwörter, SSL-Konfiguration)

Alle Konfigurationsdateien basieren auf den entsprechenden `.example` Dateien, die Sie kopieren und anpassen müssen.

### ENCRYPTION_KEY generieren (Fernet)

Sie können den Schlüssel entweder mit Python oder OpenSSL erzeugen:

- Python:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- OpenSSL (bevorzugt, überall verfügbar):
  ```bash
  openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
  ```

Den erzeugten Wert in `.env` eintragen:
```env
ENCRYPTION_KEY=...hier-ihren-schluessel-einfuegen...
```

### Neue Konfigurationsoptionen für das Multi-User-System

In der `config.yaml` wurden folgende neue Optionen hinzugefügt:

```yaml
core:
  # OTP Apprise URL template for sending OTP codes
  # Variables: {email} for user email, {otp} for the OTP code
  otp_apprise_url_template: "mailtos://smtp.example.com?to={email}&subject=TI-Monitoring OTP&body=Your OTP code is: {otp}"
  
  # Base URL for unsubscribe links
  unsubscribe_base_url: "https://ti-monitoring.example.com/unsubscribe"
```

## Abruf und Archivierung

Abruf und Archivierung erfolgen durch das Skript `cron.py`, das **selbstständig dauerhaft im Hintergrund läuft** und alle fünf Minuten neue Daten abruft.

**Hinweis**: Die folgenden Informationen gelten nur für die Python venv-Installation. Bei der Docker-Installation läuft das Skript automatisch als Container.

### Python venv-Installation

Das Skript sollte einmal gestartet werden und läuft dann kontinuierlich. Fügen Sie folgenden Eintrag in Ihre crontab ein:
```bash
crontab -e
```

Eintrag hinzufügen:
```cron
# m h  dom mon dow   command
@reboot /bin/bash -c 'source .venv/bin/activate && python cron.py'
```

Alternativ können Sie das Skript manuell starten:
```bash
source .venv/bin/activate
nohup python cron.py > cron.log 2>&1 &
```

### Docker-Installation

Bei der Docker-Installation läuft das Skript automatisch als `ti-monitoring-cron` Container und muss nicht manuell konfiguriert werden.
Die Daten werden aufbereitet und in der TimescaleDB-Datenbank gespeichert. Die Datenbank wird beim ersten Ausführen des Skriptes `cron.py` automatisch initialisiert.

**Datenbankstruktur:**
- **Tabelle `measurements`**: Speichert alle Verfügbarkeitsmessungen mit Zeitstempel, CI-ID und Status
- **Tabelle `configuration_items`**: Speichert Metadaten der CIs (Name, Produkt, Organisation)
- **Hypertables**: TimescaleDB-optimierte Zeitreihen-Tabellen für bessere Performance

**Datenaufbewahrung (Retention)**
- Konfigurierbar über `core.timescaledb.keep_days` in `config.yaml` (Standard: 185 Tage)
- TimescaleDB führt automatisch `drop_chunks` aus, um alte Daten zu entfernen
- Die Bereinigung läuft automatisch über TimescaleDB's Retention-Policy
- Optimierte Speicherung durch TimescaleDB-Komprimierung

## Benachrichtigungen

Auf Wunsch können bei Änderungen der Verfügbarkeit Benachrichtigungen versendet werden. Das System unterstützt nun über 90 verschiedene Benachrichtigungsdienste durch die Integration von Apprise, darunter:

- E-Mail (über mailto:// URLs)
- Telegram
- Slack
- Discord
- Microsoft Teams
- und viele weitere

Die Benachrichtigungen werden ebenfalls über das Skript `cron.py` versendet, sofern in der Datei `config.yaml` die Variable `notifications_enabled` den Wert `true` besitzt.

![Beispiel einer Telegram-Benachrichtigung](docs/img/screenshot-telegram.png "Beispiel einer Telegram-Benachrichtigung")

### Web-Oberfläche für Benachrichtigungseinstellungen (Multi-User OTP-System)

Ab der neuesten Version steht eine vollständig überarbeitete webbasierte Oberfläche zur Verwaltung der Benachrichtigungseinstellungen zur Verfügung. Das alte Passwort-basierte System wurde durch ein sicheres Multi-User-System mit OTP-Authentifizierung (One-Time Password) ersetzt.

#### Features des neuen Systems:

1. **Multi-User-Unterstützung**: Jeder Benutzer verwaltet seine eigenen Benachrichtigungsprofile
2. **OTP-Authentifizierung**: Sicherer Anmeldevorgang mit einmaligen Codes per E-Mail
3. **Zwei Benachrichtigungsmethoden**:
   - **Apprise**: Erweiterte Benachrichtigungen über 90+ Plattformen
   - **E-Mail**: Einfache E-Mail-Benachrichtigungen an die Anmeldeadresse
4. **CI-Auswahl**: Flexible Auswahl von Configuration Items mit Filterfunktion
5. **Datensicherheit**: Alle sensiblen Daten werden verschlüsselt in der Datenbank gespeichert
6. **Abmeldelinks**: Jedes Profil erhält einen sicheren Abmeldelink für direktes Löschen ohne Anmeldung

#### Verwendung:

1. Navigieren Sie zur "Notification Settings" Seite in der Web-App
2. Geben Sie Ihre E-Mail-Adresse ein und fordern Sie einen OTP-Code an
3. Prüfen Sie Ihr E-Mail-Postfach und geben Sie den erhaltenen Code ein
4. Nach erfolgreicher Authentifizierung können Sie Ihre Benachrichtigungsprofile verwalten

#### Konfiguration:

1. Kopieren Sie die Datei `.env.example` in `.env`:
   ```bash
   cp .env.example .env
   ```

2. Bearbeiten Sie die `config.yaml` Datei und konfigurieren Sie die OTP-Einstellungen:
   ```yaml
   core:
     # OTP Apprise URL template for sending OTP codes
     otp_apprise_url_template: "mailtos://smtp.example.com?to={email}&subject=TI-Monitoring OTP&body=Your OTP code is: {otp}"
     
     # Base URL for unsubscribe links
     unsubscribe_base_url: "https://ti-monitoring.example.com/unsubscribe"
   ```

3. Konfigurieren Sie die Apprise-URL für OTP-Versand in der `config.yaml`:
   - Beispiel für SMTP: `mailtos://username:password@smtp.gmail.com?to={email}&subject=TI-Monitoring OTP&body=Your OTP code is: {otp}`

4. Stellen Sie sicher, dass die `.env` Datei nicht in das Git-Repository eingeschlossen wird (bereits in `.gitignore` enthalten).

In der neuesten Version wurde ein Fehler behoben, bei dem der Bestätigungsdialog zum Löschen von Profilen beim Laden der Seite fälschlicherweise angezeigt wurde. Dieses Problem wurde in Version 1.2.1 behoben.

## Docker Deployment

Für detaillierte Docker-Installationsanweisungen siehe [INSTALL.md](docs/INSTALL.md).

Das TI-Monitoring kann als Docker-Container betrieben werden. Dazu ist ein Dockerfile sowie eine docker-compose.yml Datei im Projekt enthalten.

### Schnellstart

```bash
docker compose up -d
```

### Features

- **Gunicorn Web Server**: Produktionsreifer WSGI-Server mit 2 Worker-Prozessen
- **Nginx Reverse Proxy**: Mit Let's Encrypt-Unterstützung für automatische HTTPS-Zertifikate
- **Datenpersistenz**: Alle wichtigen Dateien werden als Volumes gemountet
- **Entwicklungsmodus**: `docker-compose-dev.yml` für lokale Entwicklung

## TimescaleDB-Integration (Standard)

Diese Version verwendet TimescaleDB als primäre Datenspeicherung für optimale Performance und Skalierbarkeit.

