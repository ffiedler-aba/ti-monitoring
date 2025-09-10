import json
import pytest


def test_auth_persists_across_pages(dash_duo):
    from app import app

    dash_duo.start_server(app)

    # Simuliere Login, indem wir den globalen Store in localStorage setzen
    dash_duo.driver.execute_script(
        "window.localStorage.setItem('auth-status', JSON.stringify({authenticated:true, email:'user@example.org', user_id:1}));"
    )

    # Navigiere zur Notifications-Seite
    dash_duo.driver.get(dash_duo.server_url + '/notifications')

    # Warte auf Settings-Container sichtbar
    settings = dash_duo.wait_until(lambda: dash_duo.find_element('#settings-container'))
    assert settings.is_displayed()

    # Navigiere zu Home
    dash_duo.driver.get(dash_duo.server_url + '/')
    # und zurück
    dash_duo.driver.get(dash_duo.server_url + '/notifications')

    # Wieder sichtbar
    settings2 = dash_duo.wait_until(lambda: dash_duo.find_element('#settings-container'))
    assert settings2.is_displayed()


