# CI-Ausfall-Simulation und Test-Benachrichtigungen

Dieses Dokument beschreibt die Verwendung des `simulate_ci_outage.sh` Scripts zur Simulation von Configuration Item (CI) Ausfällen und zum Testen von Benachrichtigungen.

## 🎯 Zweck

Das Script ermöglicht es:
- **CI-Ausfälle zu simulieren**: Setzt den Status einer CI auf "nicht verfügbar" (0)
- **Test-Benachrichtigungen zu senden**: Verwendet APPRISE_TEST_URL für Test-Nachrichten
- **Automatische Wiederherstellung**: Stellt die CI nach einer definierten Zeit wieder her
- **Validierung der Benachrichtigungsinfrastruktur**: Testet die gesamte Benachrichtigungskette

## 📋 Voraussetzungen

### 1. Docker Container laufen
```bash
# Container starten
scripts/docker-rebuild-dev.sh
```

### 2. APPRISE_TEST_URL konfigurieren
Fügen Sie zu Ihrer `.env` Datei hinzu:
```bash
# Beispiel für E-Mail
APPRISE_TEST_URL=mailtos://smtp.example.com?to=test@example.com&subject=TI-Monitoring Test

# Beispiel für Discord
APPRISE_TEST_URL=discord://webhook_id/webhook_token

# Beispiel für Slack
APPRISE_TEST_URL=slack://webhook_id/webhook_token
```

### 3. CI muss in der Datenbank existieren
Das Script prüft automatisch, ob die angegebene CI existiert und zeigt verfügbare CIs an.

## 🚀 Verwendung

### Grundlegende Syntax
```bash
./scripts/simulate_ci_outage.sh [CI_ID] [DURATION_MINUTES]
```

### Parameter
- **CI_ID**: Configuration Item ID (z.B. `CI-0000034`)
- **DURATION_MINUTES**: Ausfalldauer in Minuten (Standard: 5)

### Beispiele

#### 5 Minuten Ausfall für CI-0000034
```bash
./scripts/simulate_ci_outage.sh CI-0000034 5
```

#### 10 Minuten Ausfall für CI-0000123
```bash
./scripts/simulate_ci_outage.sh CI-0000123 10
```

#### Standard-Ausfalldauer (5 Minuten)
```bash
./scripts/simulate_ci_outage.sh CI-0000034
```

#### Hilfe anzeigen
```bash
./scripts/simulate_ci_outage.sh --help
```

## 📊 Was passiert während der Simulation?

### 1. Validierung
- ✅ Docker Container Status prüfen
- ✅ Datenbankverbindung testen
- ✅ CI-Existenz in Datenbank prüfen
- ✅ APPRISE_TEST_URL Konfiguration validieren

### 2. Ausfall simulieren
```sql
INSERT INTO measurements (ci, ts, status) 
VALUES ('CI-0000034', '2025-09-18 10:30:00', 0);
```

### 3. Test-Benachrichtigung senden
Das Script sendet eine detaillierte HTML-Nachricht mit:
- **Zeitstempel** der Simulation
- **CI-Informationen** (ID, Status, Dauer)
- **Technische Details** (Skript, APPRISE_URL, Simulation ID)
- **Erklärung** der Simulation

### 4. Wartezeit
Das Script wartet die angegebene Zeit und zeigt den Fortschritt an:
```
Warte 5 Minuten bis zur automatischen Wiederherstellung...
..... 5/5 Minuten
```

### 5. Wiederherstellung
```sql
INSERT INTO measurements (ci, ts, status) 
VALUES ('CI-0000034', '2025-09-18 10:35:00', 1);
```

## 📧 Test-Benachrichtigungsinhalt

### E-Mail-Beispiel
```
Betreff: TI-Monitoring Test-Benachrichtigung - CI-Ausfall Simulation

🔧 TI-Monitoring Test-Benachrichtigung

Zeit: 2025-09-18 10:30:00 UTC
CI: CI-0000034
Status: ❌ Nicht verfügbar (simuliert)
Dauer: 5 Minuten

📋 Details
Dies ist eine Test-Benachrichtigung zur Simulation eines CI-Ausfalls.
Die CI wurde manuell auf Status 0 (nicht verfügbar) gesetzt und wird nach 5 Minuten automatisch wieder auf Status 1 (verfügbar) gesetzt.

🔧 Technische Informationen
• Skript: simulate_ci_outage.sh
• APPRISE_URL: mailtos://smtp.example.com?to=test@ex...
• Simulation ID: test-1726654200

Diese Nachricht wurde automatisch vom TI-Monitoring CI-Ausfall-Simulator generiert.
```

## 🔧 Konfiguration

### APPRISE_TEST_URL Formate

#### E-Mail (SMTP)
```bash
APPRISE_TEST_URL=mailtos://smtp.example.com?to=test@example.com&subject=TI-Monitoring Test
```

#### Discord Webhook
```bash
APPRISE_TEST_URL=discord://webhook_id/webhook_token
```

#### Slack Webhook
```bash
APPRISE_TEST_URL=slack://webhook_id/webhook_token
```

#### Telegram Bot
```bash
APPRISE_TEST_URL=tgram://bot_token/chat_id
```

#### Microsoft Teams
```bash
APPRISE_TEST_URL=msteams://webhook_url
```

#### WhatsApp (via WhatsApp Business API)
```bash
APPRISE_TEST_URL=whatsapp://token:phone_number
```

### Weitere unterstützte Formate
Das Script nutzt die [Apprise-Bibliothek](https://github.com/caronc/apprise), die über 90+ Benachrichtigungsdienste unterstützt.

## 🐛 Fehlerbehebung

### Problem: "Docker Container sind nicht alle gestartet"
```bash
# Container starten
scripts/docker-rebuild-dev.sh

# Status prüfen
docker compose ps
```

### Problem: "CI CI-0000034 existiert nicht in der Datenbank"
```bash
# Verfügbare CIs anzeigen
docker compose exec -T db psql -U timonitor -d timonitor -c "SELECT ci, name FROM ci_metadata LIMIT 10;"
```

### Problem: "APPRISE_TEST_URL ist nicht konfiguriert"
```bash
# .env Datei bearbeiten
nano .env

# APPRISE_TEST_URL hinzufügen
echo "APPRISE_TEST_URL=mailtos://smtp.example.com?to=test@example.com" >> .env
```

### Problem: "Fehler beim Senden der Test-Benachrichtigung"
- ✅ APPRISE_TEST_URL Format prüfen
- ✅ Netzwerkverbindung testen
- ✅ Credentials/Schlüssel validieren
- ✅ Apprise-Dokumentation konsultieren

## 📝 Logs und Debugging

### Script-Logs
Das Script zeigt detaillierte Logs mit Farbkodierung:
- 🔵 **INFO**: Allgemeine Informationen
- 🟢 **SUCCESS**: Erfolgreiche Operationen
- 🟡 **WARNING**: Warnungen
- 🔴 **ERROR**: Fehler

### Docker Container Logs
```bash
# Web-App Logs
docker compose logs ti-monitoring-web

# Cron-Job Logs
docker compose logs ti-monitoring-cron

# Datenbank Logs
docker compose logs db
```

### Datenbankabfragen
```bash
# Letzte Messungen für eine CI
docker compose exec -T db psql -U timonitor -d timonitor -c "
SELECT ci, ts, status 
FROM measurements 
WHERE ci = 'CI-0000034' 
ORDER BY ts DESC 
LIMIT 10;
"
```

## 🔒 Sicherheitshinweise

- ✅ **Test-Umgebung**: Verwenden Sie das Script nur in Test-/Entwicklungsumgebungen
- ✅ **APPRISE_URL**: Verwenden Sie separate Test-URLs, nicht Produktions-URLs
- ✅ **Datenbank**: Das Script fügt nur Test-Daten hinzu, löscht keine bestehenden Daten
- ✅ **Rollback**: Bei Problemen können Messungen manuell aus der Datenbank entfernt werden

## 📚 Weitere Informationen

- [Apprise-Dokumentation](https://github.com/caronc/apprise)
- [TI-Monitoring Hauptdokumentation](README.md)
- [Docker-Compose Konfiguration](docker-compose-dev.yml)
- [Benachrichtigungseinstellungen](../pages/notification_settings.py)

## 🤝 Support

Bei Problemen oder Fragen:
1. Überprüfen Sie die Logs (siehe Abschnitt "Logs und Debugging")
2. Konsultieren Sie die Fehlerbehebung
3. Erstellen Sie ein Issue im GitHub Repository
4. Kontaktieren Sie das Entwicklungsteam
