# TI-Monitoring Scripts

## 📋 Übersicht

Dieses Verzeichnis enthält Hilfsskripte für die Entwicklung und Wartung der TI-Monitoring-Anwendung, insbesondere für die Callback-Verwaltung.

## 🛠️ Verfügbare Skripte

### 1. validate_callbacks.py
**Zweck**: Validiert alle Dash-Callbacks auf häufige Probleme

**Verwendung**:
```bash
# Manuelle Validierung
python scripts/validate_callbacks.py

# Mit virtuellem Environment
source .venv/bin/activate && python scripts/validate_callbacks.py
```

**Überprüft**:
- `allow_duplicate=True` erfordert `prevent_initial_call=True`
- Komplexe Callbacks (>5 Outputs)
- Doppelte Output-IDs
- Layout-Callback-Konsistenz

**Ausgabe**:
```
🔍 Validiere Callbacks in TI-Monitoring...
📄 Überprüfe notification_settings.py...
📄 Überprüfe home.py...
📄 Überprüfe plot.py...
📄 Überprüfe stats.py...
📄 Überprüfe logs.py...

📊 Validierungsergebnisse:
   Callbacks gefunden: 24
   Layout-Elemente gefunden: 37
   Fehler: 0
   Warnungen: 2

⚠️  Warnungen:
   ⚠️  notification_settings.py:1003 - Callback hat 6 Outputs (komplex)
   ⚠️  notification_settings.py:1135 - Callback hat 8 Outputs (komplex)

🎉 Alle Callbacks sind korrekt!
```

### 2. simulate_ci_outage.sh
**Zweck**: Simuliert CI-Ausfälle und sendet Test-Benachrichtigungen

**Verwendung**:
```bash
# 5 Minuten Ausfall für CI-0000034
./scripts/simulate_ci_outage.sh CI-0000034 5

# Standard-Ausfalldauer (5 Minuten)
./scripts/simulate_ci_outage.sh CI-0000034

# Hilfe anzeigen
./scripts/simulate_ci_outage.sh --help
```

**Features**:
- CI-Ausfall-Simulation (Status auf 0 setzen)
- Test-Benachrichtigungen über APPRISE_TEST_URL
- Automatische Wiederherstellung nach definierter Zeit
- Validierung von Docker-Containern und Datenbank
- Detaillierte Logs mit Farbkodierung
- Unterstützung für 90+ Benachrichtigungsdienste

**Voraussetzungen**:
- Docker Container laufen
- APPRISE_TEST_URL in .env konfiguriert
- CI muss in Datenbank existieren

### 3. callback_registry.py
**Zweck**: Registry-System für Callback-Organisation und -Validierung

**Verwendung**:
```bash
# Beispiel-Verwendung
python scripts/callback_registry.py

# In Python-Code importieren
from scripts.callback_registry import CallbackRegistry, CallbackInfo
```

**Features**:
- Callback-Registrierung mit Validierung
- Duplikat-Erkennung
- Komplexitäts-Analyse
- Bericht-Generierung
- JSON-Export/Import

## 🔧 Pre-Commit Integration

Die Skripte sind in Pre-Commit Hooks integriert und laufen automatisch bei jedem Git-Commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-callbacks
        name: Validate Dash Callbacks
        entry: .venv/bin/python scripts/validate_callbacks.py
        language: system
        files: ^pages/.*\.py$
```

## 📚 Dokumentation

- **Callback-Architektur**: `docs/callback-architecture.md`
- **Modulare Struktur**: `docs/modular-callback-structure.md`
- **CI-Ausfall-Simulation**: `docs/CI_OUTAGE_SIMULATION.md`
- **Quest-Dokumentation**: `.qoder/quests/multi-user-otp-notification.md`

## 🚨 Häufige Probleme und Lösungen

### 1. DuplicateCallback-Fehler
```
dash.exceptions.DuplicateCallback: allow_duplicate requires prevent_initial_call to be True
```

**Lösung**: Füge `prevent_initial_call=True` hinzu:
```python
@callback(
    Output('element', 'property'),
    Input('trigger', 'value'),
    allow_duplicate=True,
    prevent_initial_call=True  # ← Hinzufügen
)
```

### 2. ID not found in layout
```
ID not found in layout: 'element-id'
```

**Lösung**: 
- Überprüfe Layout-Definition
- Stelle sicher, dass Element-ID korrekt ist
- Verwende `dash.register_page()` für Seitenregistrierung

### 3. Komplexe Callbacks
```
⚠️  notification_settings.py:1003 - Callback hat 6 Outputs (komplex)
```

**Lösung**: Aufteilen in mehrere Callbacks oder Refaktorierung

## 🔄 Workflow

### Bei Callback-Änderungen
1. **Änderungen vornehmen**
2. **Validierung laufen lassen**: `python scripts/validate_callbacks.py`
3. **Tests durchführen**
4. **Commit**: Pre-Commit Hooks laufen automatisch
5. **Bei Fehlern**: Korrekturen vornehmen und wiederholen

### Bei neuen Callbacks
1. **Callback erstellen**
2. **Validierung**: `python scripts/validate_callbacks.py`
3. **Registry aktualisieren**: `python scripts/callback_registry.py`
4. **Dokumentation aktualisieren**
5. **Tests schreiben**

## 📈 Performance

### Validierung
- **Dauer**: ~1-2 Sekunden für gesamtes Projekt
- **Speicher**: Minimal (nur AST-Parsing)
- **CPU**: Niedrig (nur Datei-I/O und Parsing)

### Registry
- **Speicher**: ~1MB für 100 Callbacks
- **JSON-Export**: ~100KB für 100 Callbacks
- **Suchzeit**: O(1) für Output/Input-Lookup

## 🛡️ Sicherheit

### Datei-Zugriff
- Nur Lese-Zugriff auf Python-Dateien
- Keine Modifikation der Quelldateien
- Sichere AST-Parsing ohne Code-Ausführung

### Validierung
- Nur strukturelle Validierung
- Keine Code-Analyse oder -Ausführung
- Sichere Regex-Patterns

## 🔧 Entwicklung

### Skript erweitern
1. **Funktionalität hinzufügen**
2. **Tests schreiben**
3. **Dokumentation aktualisieren**
4. **Pre-Commit Hook testen**

### Neue Validierungsregeln
1. **Regel in `_validate_callback_rules()` hinzufügen**
2. **Test-Cases erstellen**
3. **Dokumentation aktualisieren**
4. **Mit Team abstimmen**

## 📞 Support

### Bei Problemen
1. **Logs überprüfen**: `python scripts/validate_callbacks.py 2>&1 | tee validation.log`
2. **Debug-Modus**: `python -v scripts/validate_callbacks.py`
3. **Git-Status**: `git status` und `git diff`
4. **Backup wiederherstellen**: `git checkout HEAD~1`

### Kontakt
- Entwickler: TI-Monitoring Team
- Dokumentation: `docs/callback-architecture.md`
- Issues: GitHub Issues oder Team-Chat

## 📝 Changelog

### v1.0.0 (Aktuell)
- ✅ Callback-Validierungsskript
- ✅ Pre-Commit Integration
- ✅ Callback-Registry System
- ✅ Dokumentation
- ✅ Modulare Struktur-Plan

### Geplant
- 🔄 Automatische Callback-Extraktion
- 🔄 Performance-Monitoring
- 🔄 Callback-Templates
- 🔄 Integration mit CI/CD
