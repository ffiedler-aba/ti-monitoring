import json
import pytest


def set_auth(dash_duo):
    dash_duo.driver.execute_script(
        "window.localStorage.setItem('auth-status', JSON.stringify({authenticated:true, email:'user@example.org', user_id:1}));"
    )


def test_edit_profile_opens_form(dash_duo):
    from app import app
    dash_duo.start_server(app)
    set_auth(dash_duo)

    dash_duo.driver.get(dash_duo.server_url + '/notifications')

    # Warte auf Profile-Liste
    dash_duo.wait_for_element('#profiles-container')

    # Falls es keinen Edit-Button gibt, breche test kontrolliert ab (kein Profil vorhanden)
    edit_buttons = dash_duo.find_elements('button')
    edit_btn = None
    for b in edit_buttons:
        if b.text.strip().lower() == 'bearbeiten':
            edit_btn = b
            break
    if not edit_btn:
        pytest.skip('Kein Profil vorhanden, um Edit zu testen')

    edit_btn.click()

    # Formular sollte sichtbar werden
    form = dash_duo.wait_for_element('#profile-form-container')
    assert form.is_displayed()


