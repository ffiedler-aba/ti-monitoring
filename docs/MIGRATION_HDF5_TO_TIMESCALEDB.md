# Migration von HDF5 zu TimescaleDB-only Setup

Dieses Dokument beschreibt die Migration von der HDF5-basierten Datenspeicherung zu einem reinen TimescaleDB-Setup.

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

## 🚀 Automatische Migration

### Schritt 1: Migration ausführen

```bash
# Dry-run (zeigt was gemacht würde, ohne Änderungen)
python scripts/migrate_hdf5_to_timescaledb.py --dry-run

# Echte Migration
python scripts/migrate_hdf5_to_timescaledb.py
```

### Schritt 2: Container neu starten

```bash
docker compose restart
```

### Schritt 3: Verifikation

1. Öffnen Sie die Web-Oberfläche
2. Überprüfen Sie die Statistiken-Seite
3. Testen Sie die Plot-Funktionalität
4. Prüfen Sie die Logs auf Fehler

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

## 🎉 Nach der Migration

### HDF5-Datei entfernen (optional)

```bash
# Nach erfolgreicher Verifikation
rm data/data.hdf5
```

### Docker-Volumes optimieren

```bash
# Alte HDF5-Daten aus Volume entfernen
docker run --rm -v ti-monitoring_appdata:/data alpine rm -f /data/data.hdf5
```

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
