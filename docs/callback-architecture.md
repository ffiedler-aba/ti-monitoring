# Callback-Architektur TI-Monitoring

## 📋 Übersicht

Dieses Dokument beschreibt die Callback-Architektur des TI-Monitoring Dash-Webanwendung und stellt Regeln, Best Practices und Lösungsansätze für häufige Probleme bereit.

## 🎯 Aktuelle Callback-Statistik

- **Gesamt Callbacks**: 24
- **Dateien mit Callbacks**: 5
- **Layout-Elemente**: 37
- **Komplexe Callbacks** (>5 Outputs): 2

## 📁 Callback-Verteilung

| Datei | Callbacks | Komplexität |
|-------|-----------|-------------|
| `notification_settings.py` | 21 | Hoch (2 komplexe Callbacks) |
| `home.py` | 1 | Niedrig |
| `plot.py` | 2 | Niedrig |
| `logs.py` | 1 | Niedrig |
| `stats.py` | 0 | - |

## ⚠️ Identifizierte Probleme

### 1. Komplexe Callbacks
- **notification_settings.py:1003**: 6 Outputs
- **notification_settings.py:1135**: 8 Outputs

### 2. Potentielle Risiken
- Hohe Komplexität in `notification_settings.py`
- Viele Callbacks in einer Datei
- Schwer überschaubare Abhängigkeiten

## 🛠️ Callback-Regeln

### Grundregeln

1. **allow_duplicate=True erfordert prevent_initial_call=True**
   ```python
   # ✅ Korrekt
   @callback(
       Output('element', 'property'),
       Input('trigger', 'value'),
       allow_duplicate=True,
       prevent_initial_call=True
   )
   
   # ❌ Falsch
   @callback(
       Output('element', 'property'),
       Input('trigger', 'value'),
       allow_duplicate=True  # Fehlt prevent_initial_call=True
   )
   ```

2. **Maximal 5 Outputs pro Callback**
   - Bei mehr als 5 Outputs: Aufteilen in mehrere Callbacks
   - Komplexe Callbacks erschweren Debugging und Wartung

3. **Eindeutige Callback-Namen**
   - Vermeide doppelte Output-IDs
   - Verwende beschreibende Funktionsnamen

4. **Dokumentation aller Callbacks**
   ```python
   @callback(
       Output('user-profile', 'children'),
       Input('login-button', 'n_clicks')
   )
   def handle_user_login(n_clicks):
       """
       Callback für Benutzeranmeldung
       
       Args:
           n_clicks: Anzahl Klicks auf Login-Button
       
       Returns:
           str: Benutzerprofil-HTML
       """
   ```

## 🔍 Callback-Kategorien

### 1. Authentifizierung (notification_settings.py)
- **OTP-Anfrage**: `handle_otp_request`
- **OTP-Validierung**: `handle_otp_validation`
- **Benutzeranmeldung**: `handle_user_login`
- **Benutzerabmeldung**: `handle_user_logout`

### 2. Profil-Management (notification_settings.py)
- **Profil-Erstellung**: `handle_create_profile`
- **Profil-Bearbeitung**: `handle_edit_profile`
- **Profil-Löschung**: `handle_delete_profile`
- **Profil-Test**: `handle_test_profile`

### 3. CI-Auswahl (notification_settings.py)
- **CI-Filter**: `handle_ci_filter`
- **CI-Auswahl**: `handle_ci_selection`
- **Alle auswählen**: `handle_select_all_cis`

### 4. Benachrichtigungen (notification_settings.py)
- **Apprise-Test**: `handle_test_apprise`
- **E-Mail-Test**: `handle_test_email`
- **Benachrichtigung senden**: `handle_send_notification`

### 5. UI-Interaktionen
- **Modal-Dialoge**: `handle_modal_toggle`
- **Formular-Validierung**: `handle_form_validation`
- **Dynamische Inhalte**: `handle_dynamic_content`

## 🚨 Häufige Fehler und Lösungen

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

### 3. Callback-Zyklen
```
Circular dependency detected
```

**Lösung**:
- Verwende `prevent_initial_call=True`
- Trenne Input- und Output-Callbacks
- Verwende `no_update` für unveränderte Werte

## 🔧 Debugging-Tools

### 1. Callback-Validierung
```bash
# Manuelle Validierung
python scripts/validate_callbacks.py

# Automatische Validierung (Pre-Commit)
git commit  # Läuft automatisch
```

### 2. Callback-Debugging
```python
# Debug-Informationen aktivieren
app.run_server(debug=True, dev_tools_hot_reload=True)

# Callback-Status überprüfen
app.callback_map
```

### 3. Layout-Validierung
```python
# Layout-Struktur überprüfen
print(app.layout)
```

## 📈 Performance-Optimierung

### 1. Callback-Optimierung
- Verwende `prevent_initial_call=True` für Form-Callbacks
- Minimiere Output-Anzahl pro Callback
- Verwende `no_update` für unveränderte Werte

### 2. Layout-Optimierung
- Verwende `dcc.Store` für große Datenmengen
- Implementiere Lazy Loading für große Listen
- Verwende `dash.callback_context` für bedingte Updates

## 🏗️ Refaktorierungsplan

### Phase 1: Sofortmaßnahmen ✅
- [x] Callback-Validierungsskript
- [x] Pre-Commit Hooks
- [x] Dokumentation

### Phase 2: Strukturelle Verbesserungen
- [ ] Modulare Callback-Struktur
- [ ] Callback-Registry System
- [ ] Automatisierte Tests

### Phase 3: Performance-Optimierung
- [ ] Callback-Performance-Monitoring
- [ ] Layout-Optimierung
- [ ] Caching-Strategien

## 📚 Best Practices

### 1. Callback-Design
- **Ein Verantwortlichkeitsprinzip**: Ein Callback, eine Aufgabe
- **Kurze Funktionen**: Maximal 50 Zeilen pro Callback
- **Klare Namen**: Beschreibende Funktions- und Variablennamen
- **Dokumentation**: Docstrings für alle Callbacks

### 2. Error Handling
```python
@callback(
    Output('result', 'children'),
    Input('submit', 'n_clicks')
)
def handle_submit(n_clicks):
    try:
        # Callback-Logik
        return result
    except Exception as e:
        logger.error(f"Callback-Fehler: {e}")
        return html.Div("Fehler aufgetreten", className="error")
```

### 3. State Management
```python
# Verwende dcc.Store für komplexe Zustände
dcc.Store(id='user-session', data={'user_id': None})

# Verwende callback_context für bedingte Updates
ctx = callback_context
if ctx.triggered:
    trigger_id = ctx.triggered[0]['prop_id']
```

## 🔄 Wartung und Updates

### Regelmäßige Überprüfungen
1. **Wöchentlich**: Callback-Validierung
2. **Monatlich**: Performance-Review
3. **Bei Änderungen**: Vollständige Tests

### Update-Prozess
1. Änderungen in Feature-Branch
2. Callback-Validierung läuft automatisch
3. Manuelle Tests bei komplexen Callbacks
4. Code-Review mit Fokus auf Callback-Logik
5. Deployment mit Monitoring

## 📞 Support und Hilfe

### Bei Problemen
1. **Callback-Validierung**: `python scripts/validate_callbacks.py`
2. **Debug-Modus**: `app.run_server(debug=True)`
3. **Logs überprüfen**: Docker-Container-Logs
4. **Dokumentation**: Diese Datei und Dash-Dokumentation

### Kontakt
- Entwickler: TI-Monitoring Team
- Dokumentation: `docs/callback-architecture.md`
- Validierung: `scripts/validate_callbacks.py`
