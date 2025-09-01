# TI-Monitoring

Dieses Tool dient der Überwachung verschiedener Komponenten der Telematikinfrastruktur (TI).
Es ist modular aufgebaut, sodass sich je nach Bedarf und Systemleistung auch nur einzelne Funktionen nutzen lassen.

## Vorwort

Dieses Repository entstand aus einem Fork des Originals von Lukas Schmidt-Russnak (https://github.com/lsr-dev/ti-monitoring).

Die ursprüngliche Lösung wurde erheblich erweitert und ist jetzt in einem Zustand, der einen Merge in das Original Repository problematisch erscheinen lässt.

In Absprache mit Lukas Schmidt-Russnak führe ich diesen Fork zukünfig unabhängig weiter. Einzelne Verbesserungen aus dieser erweiterten Version kann ich jedoch bei Bedarf gern in das Originalprojekt einbringen.

### Was unterscheidet dieses Projekt vom Original

- Die App wurde komplett dockerisiert; das ist die einfachste und sicherste Methode, eine komplexe Python-Anwendung mitsamt ihrer Abhängigkeiten zu deployen.
- Die E-Mail Benachrichtigung der ursprünglichen App wurde ersetzt durch die Integration von [Apprise](https://github.com/caronc/apprise). Vorteile:
  - Einfache Einbindung nahezu beliebiger Banchrichtigungsplattformen, neben SMTP-E-Mail nun auch Slack, Telegram, Teams, Mattermost, verschiedene REST-API Anbieter für E-Mail
  - Vollständige [Liste](https://github.com/caronc/apprise?tab=readme-ov-file#supported-notifications) der Benachrichtigungs-Plattformen
  - Dadurch auch Massenversand an viele Abonnenten auf unterschiedlichen Wegen möglich
- Benachrichtigungs-Konfiguration per UI über eine eigene passwortgeschützte Webpage
- Auswahl der zu abonnierenden Topics aus der Liste der *Configuration Items* der gematik API, täglich von `cron.py` aktualisiert
- Aussehen der Seite konfigurierbar (Logo, alle Texte inkl. der zugehörigen Links im Footer wie Impressum, Datenschutz u.s.w.)
- Design stellenweise überarbeitet und meinen persönlichen Vorstellungen angepasst.
- Der Darstellungs-Zeitraum der Plots ist zwischen 1 Stunde und 1 Woche frei wählbar
- Ausführliche Statisitken in den einzelnen Configuration Items und als Gesamtstatistik unter /stats

### Entwicklungsstand

Im Gegensatz zum Original TI-Monitor ist diese App als *nicht stabile Testversion* (Alpha, bestenfalls fühes Beta-Stadium) zu betrachten. Auch hier handelt es sich um ein in der Freizeit entwickeltes Privatprojekt, das weiter getrieben wird, wenn Zeit dafür übrig ist. Für Hinweise auf Bugs oder Featurewünsche habe ich jederzeit ein offenes Ohr, am liebsten als [GitHub Issue](https://github.com/elpatron68/ti-monitoring/issues).

### Öffentliche Demo-Instanz

Diese App unterscheidet sich hauptsächlich durch die Benachrichtigungsoptionen vom Original. Die Konfiguration der Notification Provider ist jedoch höchst individuell und bedarf immer der Eintragung persönlicher Daten wie Passwörter, API-Keys etc.. Aus diesem Grund gibt es von diesem Fork keine öffentliche Instanz.

### Disclaimer

Dieses Projekt wurde teilweise mithilfe von "KI" (Vibe Coding) weiter entwickelt!

## Features

Die Funktionen lassen sich wie folgt zusammenfassen:

* __Abruf und Archivierung__<br>
Die Kernfunktionalität besteht in der regelmäßigen Abfrage des Verfügbarkeitsstatus sämtlicher zentraler TI-Komponenten über eine öffentliche Schnittstelle der gematik GmbH. Die Ergebnisse werden strukturiert in einer hdf5-Datei gespeichert. So können auch für längere Beobachtungszeiträume statistische Auswertungen durchgeführt werden, um beispielsweise die Einhaltung von SLAs zu beurteilen.
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

TI-Monitoring kann sowohl mit Docker als auch mit Python venv installiert werden. Docker wird für die meisten Anwendungsfälle empfohlen.

### Schnellstart mit Docker

```bash
# Repository klonen
git clone https://github.com/lsr-dev/ti-monitoring.git
cd ti-monitoring

# Konfigurationsdateien einrichten
mkdir data
cp .env.example .env
cp notifications.json.example notifications.json
cp config.yaml.example config.yaml

# Container starten
docker compose -f docker-compose-dev.yml up -d
```

### Abhängigkeiten

Das Projekt verwendet eine requirements.txt Datei zur Verwaltung der Abhängigkeiten. Die requirements.txt Datei enthält alle notwendigen Abhängigkeiten, darunter:

- numpy, pandas, h5py für Datenverarbeitung
- requests für HTTP-Anfragen
- pytz, tzlocal für Zeitzone-Handling
- dash, plotly für die Webanwendung
- apprise für Benachrichtigungen
- python-dotenv für Umgebungsvariablen-Management
- matplotlib für Beispiele und Entwicklung

## Konfiguration

Für detaillierte Konfigurationsanweisungen siehe [INSTALL.md](docs/INSTALL.md).

Die Anwendung kann über mehrere Konfigurationsdateien konfiguriert werden:

1. **config.yaml** - Hauptkonfigurationsdatei (empfohlen)
2. **myconfig.py** - Python-basierte Konfiguration (Fallback)
3. **.env** - Umgebungsvariablen für sensible Daten
4. **notifications.json** - Benachrichtigungsprofile

Alle Konfigurationsdateien basieren auf den entsprechenden `.example` Dateien, die Sie kopieren und anpassen müssen.

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
Die Daten werden aufbereitet und in der Datei `data.hdf5` gespeichert. Existiert diese noch nicht, wird sie beim ersten Ausführen des Skriptes `cron.py` automatisch erzeugt.

Innerhalb der Datei wird folgende Gruppenstruktur aufgebaut:

```
.
+-- availability
|   +-- CI-0000001
|   +-- CI-0000002
|   +-- ...
+-- configuration_items
    +-- CI-0000001
    +-- CI-0000002
    +-- ...
```

Die Gruppen `availability` und `configuration_items` enthalten jeweils für jedes Konfigurationsobjekt (z.B. `CI-0000001`) eine gleichnamige Untergruppe.

Die Untergruppe des Konfigurationsobjektes in der Gruppe `availability` enthält Datensätze mit der Verfügbarkeit als Integer (0: nicht verfügbar, 1: verfügbar). Der Name des Datensatzes entspricht der Unix-Zeit des Datenpunktes. Bei Aktualisierungen wird ein neuer Datensatz hinzugefügt.

Die Untergruppe des Konfigurationsobjektes in der Gruppe `configuration_items` enthält mehrere Datensätze mit allegemeinen Eigenschaften wie `name`, `product` und `organization`. Außerdem die aktuelle Verfügbarkeit `current_availability` sowie die Veränderung der Verfügbarkeit `availability_difference` in Bezug auf den vorherigen Wert (-1: nicht mehr verfügbar, 0: keine Veränderung, 1: wieder verfügbar). Bei Aktualisierungen werden die vorhandenen Datensätze überschrieben.

Je nach Systemleistung kann es sinnvoll sein, die Datei `data.hdf5` von Zeit zu Zeit archivieren. Hierzu kann die Datei beispielsweise per Cronjob in ein Archiv-Verzeichnis verschoben werden.

## Benachrichtigungen

Auf Wunsch können bei Änderungen der Verfügbarkeit Benachrichtigungen versendet werden. Das System unterstützt nun über 90 verschiedene Benachrichtigungsdienste durch die Integration von Apprise, darunter:

- E-Mail (über mailto:// URLs)
- Telegram
- Slack
- Discord
- Microsoft Teams
- und viele weitere

Die Benachrichtigungen werden ebenfalls über das Skript `cron.py` versendet, sofern in der Datei `myconfig.py` die Variable `notifications` den Wert `True` besitzt.

![Beispiel einer Telegram-Benachrichtigung](docs/img/screenshot-telegram.png "Beispiel einer Telegram-Benachrichtigung")

### Web-Oberfläche für Benachrichtigungseinstellungen

Ab Version 1.2.0 steht eine webbasierte Oberfläche zur Verwaltung der Benachrichtigungseinstellungen zur Verfügung. Über die Seite "Notification Settings" in der Web-App können Benachrichtigungsprofile erstellt, bearbeitet und gelöscht werden.

![Screenshot der Notifications-Seite](docs/img/screenshot_notification-page.png "Screenshot der Notifications-Seite - Einheitliche Breite aller Elemente und responsives Design")

Die Seite ist durch ein einfaches Passwortschutzsystem gesichert. Das Passwort wird über eine Umgebungsvariable `NOTIFICATION_SETTINGS_PASSWORD` konfiguriert, die in einer `.env` Datei im Projektverzeichnis gespeichert wird.

In der Datei `notifications.json` können mehrere Profile definiert werden. Ein Profil besteht aus folgenden Eigenschaften:

| Name | Beschreibung |
| ----------- | ----------- |
| name | Name des Profils (wird in der Anrede verwendet) |
| apprise_urls | Liste mit mindestens einer Apprise-URL (z.B. `["mailto://user:pass@gmail.com", "tgram://bottoken/ChatID"]`) |
| ci_list | Liste von Konfigurationsobjekten (z.B. `["CI-000001", "CI-0000002"]`) |
| type | entweder `blacklist` oder `whitelist` (legt fest, wie die Liste der Konfigurationsobjekte behandelt wird) |

Die neue Konfigurationsstruktur ist abwärtskompatibel - bestehende E-Mail-Konfigurationen mit dem Feld `recipients` funktionieren weiterhin.

Um den Passwortschutz zu konfigurieren:

1. Kopieren Sie die Datei `.env.example` in `.env`:
   ```bash
   cp .env.example .env
   ```

2. Bearbeiten Sie die `.env` Datei und setzen Sie ein sicheres Passwort:
   ```bash
   NOTIFICATION_SETTINGS_PASSWORD=IhrSicheresPasswortHier
   ```

3. Stellen Sie sicher, dass die `.env` Datei nicht in das Git-Repository eingeschlossen wird (bereits in `.gitignore` enthalten).

Nach der Konfiguration können Sie über den Navigationslink "Notification Settings" auf die Einstellungsseite zugreifen und sich mit dem konfigurierten Passwort anmelden.

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

## Web-App

Der aktuelle Status verschiedener Komponenten kann optional auch in Form einer Web-App auf Basis des [Dash-Frameworks](https://dash.plotly.com) bereitgestellt werden. Die App kann z.B. in Kombination mit uWSGi und nginx (ähnlich [wie hier beschrieben](https://carpiero.medium.com/host-a-dashboard-using-python-dash-and-linux-in-your-own-linux-server-85d891e960bc) veröffentlicht werden.

Auf der Startseite der App werden die Komponenten nach Produkt gruppiert dargestellt. Durch Anklicken der Gruppen lassen sich die jeweiligen Komponenten einblenden.
![Screenshot aus der App: Startseite der App (Beispiel)](docs/img/App%20Home%20Beispiel.png "Startseite der App (Beispiel)")
![Screenshot aus der App: Startseite der App mit Störung (Beispiel)](docs/img/App%20Home%20Beispiel%20Störung.png "Startseite der App mit Störung (Beispiel)")
Per Klick auf die ID einer Komponente lässt sich eine Statistik der letzten Stunden aufrufen.
![Screenshot aus der App: Statistik für eine Komponente (Beispiel)](docs/img/App%20Statistik%20Beispiel.png "Screenshot aus der App: Statistik für eine Komponente (Beispiel)")

### Individuelle Zeitraum-Anpassung

Ab Version 1.3.0 können Benutzer den Darstellungszeitraum für jeden Plot individuell anpassen. Über ein Dropdown-Menü können verschiedene Zeiträume von 1 Stunde bis zu 1 Woche ausgewählt werden. Der Standardwert wird aus der `config.yaml` Datei übernommen und kann dort global konfiguriert werden.

**Verfügbare Zeiträume:**
- 1 Stunde
- 3 Stunden  
- 6 Stunden
- 12 Stunden (Standard)
- 24 Stunden
- 48 Stunden
- 72 Stunden
- 1 Woche (168 Stunden)

Der gewählte Zeitraum wird in der URL gespeichert, sodass er bei der nächsten Nutzung beibehalten wird.

Um eine gute Performance zu gewährleisten, kann das Zeitfenster der Statistik über die Variable `stats_delta_hours` in der Datei `config.yaml` reduziert werden. Zudem kann es ratsam sein, die Datei `data.hdf5` regelmäßig zu archivieren bzw. zu leeren.

Soll die Web-App überhaupt nicht genutzt werden, sind folgende Ordner bzw. Dateien irrelevant und können entfernt werden:

* assets
* pages
* app.py

## Statistiken-Seite

Ab Version 1.4.0 steht eine dedizierte Statistiken-Seite zur Verfügung, die eine umfassende Gesamtübersicht aller Configuration Items (CIs) bereitstellt. Die Seite ist über den Navigationslink "Stats" (Analytics-Icon) in der Web-App erreichbar.

![Screenshot der Statistiken-Seite](docs/img/screenshot-stats-page.png "Screenshot der Statistiken-Seite - Umfassende Gesamtstatistiken aller Configuration Items")

### Verfügbare Statistiken

Die Statistiken-Seite bietet folgende Informationen:

#### 🎯 Übersicht
- **Gesamtanzahl CIs**: Anzahl aller überwachten Configuration Items
- **Aktuell verfügbar**: Anzahl der derzeit verfügbaren CIs
- **Aktuell nicht verfügbar**: Anzahl der derzeit nicht verfügbaren CIs
- **Gesamtverfügbarkeit**: Prozentsatz der verfügbaren CIs

#### 📅 Datenstatus
- **Letzte Aktualisierung**: Zeitstempel der letzten Datenaktualisierung (Europe/Berlin)
- **Datenalter**: Wie alt die aktuellen Daten sind
- **Kürzliche Änderungen**: Anzahl der CIs mit Statusänderungen

#### 🏢 Struktur
- **Produkte**: Anzahl der verschiedenen Produktkategorien
- **Organisationen**: Anzahl der verschiedenen Organisationen

#### 🔴 Summierte Ausfallzeiten aller CIs
- **Gesamtausfallzeit**: Absolute Summe aller Ausfallzeiten in Minuten
- **Gesamtausfallzeit (⌀ pro Tag)**: Durchschnittliche Ausfallzeit pro Tag
- **Gesamtausfallzeit (⌀ pro Woche)**: Durchschnittliche Ausfallzeit pro Woche
- **Gesamtausfallzeit (⌀ pro Jahr)**: Durchschnittliche Ausfallzeit pro Jahr

#### 📈 Durchschnittliche Ausfallzeiten pro Zeitintervall
- **Pro Tag**: Durchschnittliche Ausfallzeit pro Tag über den gesamten Aufzeichnungszeitraum
- **Pro Woche**: Durchschnittliche Ausfallzeit pro Woche über den gesamten Aufzeichnungszeitraum
- **Pro Jahr**: Durchschnittliche Ausfallzeit pro Jahr über den gesamten Aufzeichnungszeitraum

### Performance-Optimierung

Die Statistiken werden gecacht, um die Ladezeiten zu optimieren:
- **Cache-TTL**: 5 Minuten
- **Automatische Erneuerung**: Statistiken werden automatisch neu berechnet, wenn der Cache abläuft
- **Cache-Informationen**: Anzeige der letzten Berechnung und verbleibenden Cache-Zeit

### Berechnungsmethodik

Die Ausfallzeit-Statistiken basieren auf einer Stichprobe der CIs (maximal 20 CIs) zur Performance-Optimierung:
- **Sampling**: Repräsentative Stichprobe mit festem Seed für konsistente Ergebnisse
- **Skalierung**: Ergebnisse werden auf die Gesamtanzahl der CIs hochskaliert
- **Zeitbasis**: Berechnungen basieren auf dem gesamten Aufzeichnungszeitraum aller CIs

---

**DISCLAIMER**

Es handelt sich um ein privates Projekt ohne offiziellen Support. Jegliche Nutzung erfolgt auf eigene Verantwortung. 

Die Daten werden über eine öffentlich erreichbare Schnittstelle der gematik GmbH abgerufen. Eine ausführliche Beschreibung diser Schnittstelle ist öffentlich auf GitHub verfügbar: [https://github.com/gematik/api-tilage](https://github.com/gematik/api-tilage).

---