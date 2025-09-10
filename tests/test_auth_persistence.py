import json
import pytest
import sys
from pathlib import Path

# Ensure project root is in sys.path for `import app`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_auth_persists_across_pages(dash_duo):
    from app import app

    dash_duo.start_server(app)

    # Simuliere Login, indem wir den globalen Store in localStorage setzen
    dash_duo.driver.execute_script(
        "window.localStorage.setItem('auth-status', JSON.stringify({authenticated:true, email:'user@example.org', user_id:1}));"
    )

    # Navigiere zur Notifications-Seite
    dash_duo.driver.get(dash_duo.server_url + '/notifications')

    # Prüfe Persistenz im localStorage nach Navigation
    auth_json = dash_duo.driver.execute_script("return window.localStorage.getItem('auth-status');")
    assert auth_json, 'auth-status missing after navigation to /notifications'
    auth = json.loads(auth_json)
    assert auth.get('authenticated') is True

    # Navigiere zu Home
    dash_duo.driver.get(dash_duo.server_url + '/')
    # und zurück
    dash_duo.driver.get(dash_duo.server_url + '/notifications')

    # Persistenz erneut prüfen nach Seitenwechsel zurück
    auth_json2 = dash_duo.driver.execute_script("return window.localStorage.getItem('auth-status');")
    assert auth_json2, 'auth-status missing after navigating back to /notifications'
    auth2 = json.loads(auth_json2)
    assert auth2.get('authenticated') is True


