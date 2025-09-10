# Tests und Validierung

Dieses Dokument beschreibt, wie die Test- und Validierungs-Umgebung des TI‑Monitoring Projekts verwendet wird.

## Überblick
- **Callback‑Validierung**: Statische Prüfung aller Dash‑Callbacks auf häufige Fehler (One‑Writer‑Prinzip, kein `allow_duplicate=True`, korrekte Rückgabearitäten, u.a.).
- **Nicht‑UI Tests (Pytest)**: Schnelle Tests ohne Browser/GUI. DB‑bezogene Tests sind optional schaltbar.
- **UI/E2E‑Tests (Dash Testing)**: Interaktive End‑to‑End‑Tests mit Headless‑Chrome via `dash[testing]`/Selenium.

## Voraussetzungen
- **Lokale Ausführung**: Empfohlen innerhalb des Projekt‑Venv
```bash
source .venv/bin/activate
```
- **UI‑Tests** benötigen einen WebDriver. Unter Ubuntu/Debian z. B.:
```bash
sudo apt-get update && sudo apt-get install -y chromium-driver
```
- **Datenbanktests**: Die TimescaleDB ist im lokalen Setup nur aus dem Docker‑Container erreichbar (siehe `docker-compose-dev.yml`). Für echte DB‑Tests empfiehlt sich die Ausführung in den Containern.

## Umgebungsvariablen
- `DASH_E2E=1` aktiviert UI/E2E‑Tests. Ohne diese Variable werden UI‑Tests übersprungen.
- `RUN_DB_TESTS=1` aktiviert DB‑gebundene Tests (z. B. OTP‑Systemtest). Ohne diese Variable werden sie übersprungen.
- `ENCRYPTION_KEY` optional für Entschlüsselungstests (z. B. Apprise‑URLs, E‑Mail). Wenn nicht gesetzt, wird im Code ein Key generiert (nur für Laufzeit, nicht persistiert).

## Callback‑Validierung
- Skript: `validate_callbacks.py`
- Strikter Lauf:
```bash
source .venv/bin/activate
python validate_callbacks.py --strict
```
- Prüft u. a.:
  - One‑Writer‑Prinzip (jede Output‑ID nur von genau einem Callback beschrieben)
  - Kein `allow_duplicate=True`
  - Plausible Argumentanzahlen und Rückgabearitäten
  - Warnung bei übermäßig vielen Outputs je Callback

## Nicht‑UI Tests (schnell)
- Pytest ohne UI/E2E‑Teile:
```bash
source .venv/bin/activate
pytest -q -k "not dash and not e2e"
```
- Relevante Tests/Dateien:
  - `tests/test_validator_policy.py`: Führt `validate_callbacks.py --strict` aus (nutzt `sys.executable`).
  - `scripts/test_otp_system.py`: In Pytest konvertierter OTP‑Systemtest. Wird nur ausgeführt, wenn `RUN_DB_TESTS=1` gesetzt ist.
  - `tests/conftest.py`: Pytest‑Konfiguration (z. B. Überspringen von UI‑Tests, Headless‑Chrome‑Optionen).
  - `pytest.ini`: Setzt `pythonpath = .` für saubere Imports aus dem Projekt‑Root.

## UI/E2E‑Tests
- Aktivierung über Umgebungsvariable und Ausführung einzelner Tests:
```bash
export DASH_E2E=1
source .venv/bin/activate
pytest -q tests/test_auth_persistence.py::test_auth_persists_on_navigation
pytest -q tests/test_edit_profile_flow.py::test_edit_profile_prefills_form
```
- Hinweise:
  - UI‑Tests verwenden `dash[testing]`/`dash_duo` und starten die App testweise.
  - `tests/conftest.py` konfiguriert Headless‑Chrome und überspringt die Tests ohne `DASH_E2E=1`.
  - Für Browser/WebDriver: siehe Abschnitt „Voraussetzungen“.

## Datenbankgebundene Tests im Container
- Da die DB nur im Compose‑Netz erreichbar ist, empfiehlt sich die Ausführung innerhalb des Web‑Containers:
```bash
docker compose -f docker-compose-dev.yml exec -T ti-monitoring-web bash -lc "python -m pytest -q -k 'not dash and not e2e'"
docker compose -f docker-compose-dev.yml exec -T ti-monitoring-web bash -lc "python validate_callbacks.py --strict"
```
- Für OTP‑/DB‑Tests:
```bash
docker compose -f docker-compose-dev.yml exec -T ti-monitoring-web bash -lc "export RUN_DB_TESTS=1 && python -m pytest -q scripts/test_otp_system.py"
```

## Manuelle/integrierte Simulation (optional, hilft bei End‑to‑End‑Prüfung)
- Skript: `scripts/simulate_notifications.py`
- Simuliert reale Statusänderungen über DB‑Einträge und triggert anschließend `send_db_notifications()`.
- Ausführung im Web‑Container (empfohlen):
```bash
docker compose -f docker-compose-dev.yml exec -T ti-monitoring-web bash -lc "python scripts/simulate_notifications.py --method db --mode incident"
```
  - Optionen:
    - `--method`: `db` (echte Messwerte schreiben) oder `mock` (nur DF manipulieren)
    - `--mode`: `incident` | `recovery` | `toggle`
    - `--ci`: CI‑ID (optional; wenn leer, wird eine beliebige CI gewählt)

## Troubleshooting
- `ModuleNotFoundError: app`: Stelle sicher, dass `pytest.ini` mit `pythonpath = .` vorhanden ist oder `PYTHONPATH` gesetzt ist.
- `chromedriver` nicht gefunden: Installiere `chromium-driver` (oder passenden WebDriver) und stelle sicher, dass er im PATH liegt.
- DB‑Zugriff schlägt lokal fehl: DB‑Tests innerhalb der Docker‑Container ausführen (Compose‑Netz).
- Apprise‑Benachrichtigungen fehlen: Prüfe, ob Apprise‑URLs entschlüsselbar sind (`ENCRYPTION_KEY`/Salts vorhanden) und ob der jeweilige Provider korrekt erreichbar/konfiguriert ist.
