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

## ⚠️ Häufige Probleme und Lösungen

### Problem 1: Datenbankverbindung außerhalb des Docker-Netzwerks

**Symptom:**
```
psycopg2.OperationalError: could not translate host name "db" to address: Temporary failure in name resolution
```

**Ursache:** Migration-Skripte werden lokal ausgeführt, aber versuchen sich mit dem Docker-Service-Namen `db` zu verbinden.

**Lösung:**
```bash
# .env-Datei für lokale Ausführung anpassen
echo "POSTGRES_HOST=localhost" >> .env
echo "POSTGRES_PORT=5432" >> .env

# Oder config.yaml temporär auf localhost ändern
sed -i 's/host: db/host: localhost/g' config.yaml
```

### Problem 2: Migration-Skript im Container nicht gefunden

**Symptom:**
```
python: can't open file '/app/scripts/migrate_hdf5_to_timescaledb.py': [Errno 2] No such file or directory
```

**Ursache:** Das `scripts/`-Verzeichnis ist nicht in den Web-Container gemountet.

**Lösung:** Migration-Skripte lokal ausführen, nicht im Container.

### Problem 3: Web-Anwendung lädt keine Daten

**Symptom:** Hauptseite zeigt nur Header und Footer, keine CI-Daten.

**Ursache:** `file_name` Variable wurde aus `config.yaml` entfernt, aber Code versucht noch darauf zuzugreifen.

**Lösung:**
```python
# In pages/home.py und pages/stats.py
config_file_name = None  # Statt config_file_name = core_config.get('file_name')
cis = get_data_of_all_cis_from_timescaledb()  # Statt HDF5-Funktionen
```

### Problem 4: SQL-Query Spalten stimmen nicht mit DataFrame überein

**Symptom:**
```
KeyError: 'current_availability' oder 'name'
```

**Ursache:** SQL-Query gibt andere Spalten zurück als im `pd.DataFrame`-Konstruktor erwartet.

**Lösung:**
```python
# In mylibrary.py - Spalten explizit definieren
columns = ['ci', 'timestamp', 'status', 'response_time', 'current_availability', 
           'name', 'organization', 'product', 'bu', 'tid', 'pdt', 'comment']
df = pd.DataFrame(results, columns=columns)
```

### Problem 5: NULL-Werte in SQL-Queries verursachen TypeError

**Symptom:**
```
TypeError: can only concatenate str (not "NoneType") to str
```

**Ursache:** SQL-Query gibt `NULL`-Werte zurück, die in Python zu `None` werden.

**Lösung:**
```sql
-- COALESCE verwenden für alle String-Spalten
SELECT ci, timestamp, status, response_time, current_availability,
       COALESCE(name, '') as name,
       COALESCE(organization, '') as organization,
       COALESCE(product, '') as product,
       COALESCE(bu, '') as bu,
       COALESCE(tid, '') as tid,
       COALESCE(pdt, '') as pdt,
       COALESCE(comment, '') as comment
FROM measurements m
LEFT JOIN ci_metadata c ON m.ci = c.ci
```

### Problem 6: pandas Timestamp-Objekte in pretty_timestamp

**Symptom:**
```
TypeError: strptime() argument 1 must be str, not Timestamp
```

**Ursache:** `pretty_timestamp` Funktion erwartet String, bekommt aber pandas Timestamp-Objekt.

**Lösung:**
```python
def pretty_timestamp(timestamp):
    if hasattr(timestamp, 'to_pydatetime'):
        # pandas Timestamp-Objekt
        utc_time = timestamp.to_pydatetime()
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=pytz.UTC)
    else:
        # String-Timestamp
        utc_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
    
    berlin_time = utc_time.astimezone(pytz.timezone('Europe/Berlin'))
    return berlin_time.strftime('%d.%m.%Y %H:%M:%S Uhr')
```

### Problem 7: ci_metadata Tabelle ist leer

**Symptom:** Plot-Seiten sind leer, keine Metadaten verfügbar.

**Ursache:** Migration hat nur `measurements` Tabelle gefüllt, aber `ci_metadata` ist leer.

**Lösung:**
```sql
-- ci_metadata mit Standard-Werten füllen
INSERT INTO ci_metadata (ci, name, organization, product, bu, tid, pdt, comment)
SELECT DISTINCT ci, ci as name, '' as organization, '' as product, 
                '' as bu, '' as tid, '' as pdt, '' as comment
FROM measurements
ON CONFLICT (ci) DO NOTHING;

-- Dann mit echten Metadaten aus ci_list.json aktualisieren
```

### Problem 8: Docker-Volumes sind read-only

**Symptom:**
```
sed: cannot rename /app/sedIjVZma: Device or resource busy
```

**Ursache:** Versuch, gemountete Dateien im Container zu bearbeiten.

**Lösung:** Dateien auf dem Host bearbeiten, dann Container neu starten.

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
