# Migration von HDF5 zu TimescaleDB-only Setup ✅ ABGESCHLOSSEN

**Status**: Diese Migration wurde erfolgreich abgeschlossen. TimescaleDB ist jetzt die Standard-Datenspeicherung.

Dieses Dokument beschreibt die abgeschlossene Migration von der HDF5-basierten Datenspeicherung zu einem reinen TimescaleDB-Setup.

## 🎯 Ziel

Die Anwendung soll vollständig auf TimescaleDB umgestellt werden, um:
- Bessere Performance bei großen Datenmengen zu erreichen
- Erweiterte SQL-Abfragen zu ermöglichen
- Skalierbarkeit zu verbessern
- Wartungsaufwand zu reduzieren

## 📋 Voraussetzungen

- TimescaleDB-Container läuft (`docker compose --profile tsdb up -d`)
- TimescaleDB ist in `config.yaml` aktiviert (`timescaledb.enabled: true`)
- HDF5-Datei existiert und enthält Daten (`data/data.hdf5`)

## ✅ Migration abgeschlossen

Die Migration wurde erfolgreich durchgeführt. Alle HDF5-Fallbacks wurden entfernt und TimescaleDB ist jetzt die einzige Datenspeicherung.

### Was wurde geändert:

1. **Code-Änderungen**:
   - `mylibrary.py`: Alle HDF5-Funktionen entfernt, nur noch TimescaleDB
   - `cron.py`: Komplett für TimescaleDB umgeschrieben
   - `pages/stats.py`: HDF5-Fallbacks entfernt
   - `pages/notification_settings.py`: HDF5-Zugriff entfernt

2. **Konfiguration**:
   - `config.yaml`: TimescaleDB als Standard konfiguriert
   - Alle Docker-Compose-Dateien: `.env`-Mount hinzugefügt

3. **Dokumentation**:
   - README.md: HDF5-Referenzen durch TimescaleDB ersetzt
   - INSTALL.md: Installation für TimescaleDB aktualisiert
   - Windows-Dokumentation: HDF5-Referenzen entfernt

## 🔧 Manuelle Migration

Falls die automatische Migration nicht funktioniert:

### 1. Konfiguration aktualisieren

```yaml
# config.yaml
core:
  # Entfernen Sie diese Zeile:
  # file_name: "data/data.hdf5"
  
  # Stellen Sie sicher, dass TimescaleDB aktiviert ist:
  timescaledb:
    enabled: true
    host: "db"
    port: 5432
    dbname: "timonitor"
    user: "timonitor"
    password: "timonitor"
```

### 2. Daten migrieren

```bash
# HDF5-Daten nach TimescaleDB importieren
python scripts/backfill_timescaledb.py data/data.hdf5
```

### 3. Container neu starten

```bash
docker compose restart
```

## ⚠️ Wichtige Hinweise

### Backup erstellen

**Vor der Migration:**
```bash
# Konfiguration sichern
cp config.yaml config.yaml.backup

# HDF5-Daten sichern
cp data/data.hdf5 data/data.hdf5.backup

# Docker-Volumes sichern
docker run --rm -v ti-monitoring_appdata:/data -v $(pwd):/backup alpine tar czf /backup/appdata-backup.tar.gz -C /data .
```

### Rollback (falls nötig)

```bash
# Konfiguration zurücksetzen
cp config.yaml.backup config.yaml

# HDF5-Datei zurücksetzen
cp data/data.hdf5.backup data/data.hdf5

# Container neu starten
docker compose restart
```

## 🔍 Verifikation

### 1. Datenbank prüfen

```bash
# In den Web-Container einsteigen
docker exec -it ti-monitoring-ti-monitoring-web-1 bash

# Datenbank verbinden
python3 -c "
import psycopg2
conn = psycopg2.connect(host='db', database='timonitor', user='timonitor', password='timonitor')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM measurements')
print(f'Messungen in TimescaleDB: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(DISTINCT ci) FROM measurements')
print(f'Eindeutige CIs: {cur.fetchone()[0]}')
conn.close()
"
```

### 2. Web-Interface prüfen

- **Startseite**: Alle CIs sollten angezeigt werden
- **Statistiken**: Realistische Verfügbarkeitswerte (nicht 100%)
- **Plots**: Zeitreihen sollten korrekt angezeigt werden
- **Logs**: Keine HDF5-Fehler in den Container-Logs

## 🐛 Troubleshooting

### Problem: "relation 'measurements' does not exist"

**Lösung:**
```bash
# TimescaleDB-Schema initialisieren
docker exec ti-monitoring-ti-monitoring-web-1 python3 -c "
from mylibrary import init_timescaledb_schema
init_timescaledb_schema()
print('Schema initialized')
"
```

### Problem: Keine Daten in der Web-Oberfläche

**Lösung:**
```bash
# Daten manuell migrieren
docker exec ti-monitoring-ti-monitoring-web-1 python3 -c "
from mylibrary import ingest_hdf5_to_timescaledb
rows = ingest_hdf5_to_timescaledb('data/data.hdf5')
print(f'Migrated {rows} rows')
"
```

### Problem: Container startet nicht

**Lösung:**
```bash
# Logs prüfen
docker logs ti-monitoring-ti-monitoring-web-1

# Konfiguration validieren
docker exec ti-monitoring-ti-monitoring-web-1 python3 -c "
from mylibrary import load_config
config = load_config()
print('Config loaded successfully')
"
```

## 📊 Performance-Vergleich

| Aspekt | HDF5 | TimescaleDB |
|--------|------|-------------|
| Lese-Performance | Gut | Sehr gut |
| Schreib-Performance | Sehr gut | Gut |
| Speicherverbrauch | Niedrig | Mittel |
| SQL-Abfragen | Nein | Ja |
| Skalierbarkeit | Begrenzt | Sehr gut |
| Wartung | Komplex | Einfach |

## 🎉 Migration erfolgreich abgeschlossen

### HDF5-Dateien entfernt

Alle HDF5-Dateien und -Referenzen wurden aus dem System entfernt:
- `data/data.hdf5` - Nicht mehr verwendet
- HDF5-Fallbacks im Code - Entfernt
- HDF5-Abhängigkeiten - Entfernt

### Aktuelle Architektur

Das System verwendet jetzt ausschließlich:
- **TimescaleDB** als primäre Datenspeicherung
- **PostgreSQL** als Basis-Datenbank
- **Hypertables** für optimierte Zeitreihen-Performance
- **Automatische Retention** über TimescaleDB-Policies

### Monitoring einrichten

```bash
# TimescaleDB-Performance überwachen
docker exec ti-monitoring-ti-monitoring-web-1 python3 -c "
import psycopg2
conn = psycopg2.connect(host='db', database='timonitor', user='timonitor', password='timonitor')
cur = conn.cursor()
cur.execute('SELECT pg_size_pretty(pg_database_size(current_database()))')
print(f'Datenbankgröße: {cur.fetchone()[0]}')
conn.close()
"
```

## 📞 Support

Bei Problemen:
1. Prüfen Sie die Container-Logs
2. Überprüfen Sie die TimescaleDB-Verbindung
3. Testen Sie mit dem Migration-Skript im Dry-Run-Modus
4. Erstellen Sie ein Issue im GitHub-Repository
