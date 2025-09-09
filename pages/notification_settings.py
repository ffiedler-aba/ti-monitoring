import dash
from dash import html, dcc, Input, Output, State, callback, no_update, callback_context
import json
from mylibrary import *
import yaml
import os
import apprise
import secrets
from datetime import datetime

# Modern button styles (unchanged)
MODERN_BUTTON_STYLES = {
    'primary': {
        'backgroundColor': '#007bff',
        'color': 'white',
        'border': 'none',
        'padding': '10px 20px',
        'borderRadius': '8px',
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 4px rgba(0, 123, 255, 0.2)',
        'margin': '5px'
    },
    'secondary': {
        'backgroundColor': '#6c757d',
        'color': 'white',
        'border': 'none',
        'padding': '10px 20px',
        'borderRadius': '8px',
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 4px rgba(108, 117, 125, 0.2)',
        'margin': '5px'
    },
    'success': {
        'backgroundColor': '#28a745',
        'color': 'white',
        'border': 'none',
        'padding': '10px 20px',
        'borderRadius': '8px',
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 4px rgba(40, 167, 69, 0.2)',
        'margin': '5px'
    },
    'danger': {
        'backgroundColor': '#dc3545',
        'color': 'white',
        'border': 'none',
        'padding': '10px 20px',
        'borderRadius': '8px',
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 4px rgba(220, 53, 69, 0.2)',
        'margin': '5px'
    },
    'warning': {
        'backgroundColor': '#ffc107',
        'color': '#212529',
        'border': 'none',
        'padding': '10px 20px',
        'borderRadius': '8px',
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 4px rgba(255, 193, 7, 0.2)',
        'margin': '5px'
    }
}

def get_button_style(button_type='primary'):
    return MODERN_BUTTON_STYLES[button_type].copy()

def get_error_style(visible=True):
    base_style = {
        'color': '#e74c3c',
        'marginBottom': '15px',
        'fontWeight': '500',
        'padding': '10px',
        'backgroundColor': '#fdf2f2',
        'borderRadius': '6px',
        'border': '1px solid #fecaca'
    }
    base_style['display'] = 'block' if visible else 'none'
    return base_style

def load_config():
    """Load configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except (FileNotFoundError, Exception):
        return {}

def load_core_config():
    """Load core configuration from YAML file"""
    config = load_config()
    return config.get('core', {})

def serve_layout():
    """Clean, refactored layout with separate stores"""
    return html.Div([
        html.H2('Benachrichtigungseinstellungen', style={
            'color': '#2c3e50',
            'fontWeight': '600',
            'marginBottom': '30px',
            'borderBottom': '2px solid #3498db',
            'paddingBottom': '10px'
        }),

        # === STORES (Single source of truth) ===
        dcc.Store(id='auth-status', storage_type='local'),
        dcc.Store(id='auth-state-store', data={'authenticated': False}),
        dcc.Store(id='otp-state-store', data={'step': 'login', 'email': ''}),
        dcc.Store(id='ui-state-store', data={'show_login': True, 'show_otp': False, 'show_settings': False}),

        # === UI CONTAINERS (Controlled by stores) ===
        # Login container
        html.Div(id='otp-login-container', children=[
            html.H3('OTP-Anmeldung erforderlich'),
            html.P('Bitte geben Sie Ihre E-Mail-Adresse ein, um einen OTP-Code zu erhalten.'),
            dcc.Input(id='email-input', type='email', placeholder='E-Mail-Adresse eingeben', style={'width': '100%', 'marginBottom': '15px', 'padding': '12px', 'borderRadius': '8px'}),
            html.Button('OTP anfordern', id='request-otp-button', n_clicks=0, style=get_button_style('primary')),
            html.Div(id='otp-request-error', style={'color': '#e74c3c', 'marginTop': '15px'})
        ], style={'display': 'block', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)', 'marginBottom': '20px'}),

        # OTP code container
        html.Div(id='otp-code-container', children=[
            html.H3('OTP-Code eingeben'),
            html.P(id='otp-instructions', children='Bitte geben Sie den 6-stelligen Code ein.'),
            dcc.Input(id='otp-code-input', type='text', placeholder='6-stelliger Code', style={'width': '100%', 'marginBottom': '15px', 'padding': '12px', 'borderRadius': '8px'}),
            html.Button('Anmelden', id='verify-otp-button', n_clicks=0, style=get_button_style('primary')),
            html.Button('Neuen Code anfordern', id='resend-otp-button', n_clicks=0, style=get_button_style('secondary')),
            html.Div(id='otp-verify-error', style={'color': '#e74c3c', 'marginTop': '15px'})
        ], style={'display': 'none', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)', 'marginBottom': '20px'}),

        # Settings container
        html.Div(id='settings-container', children=[
            html.Div(id='user-info', children='', style={'marginBottom': '20px', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'}),
            html.P('Verwalten Sie Ihre Benachrichtigungsprofile unten.'),
            html.Div(id='profiles-container'),
            html.Button('Neues Profil hinzufügen', id='add-profile-button', n_clicks=0, style=get_button_style('success')),

            # Profile form (hidden by default)
            html.Div(id='profile-form-container', children=[
                html.H3('Neues Profil erstellen'),
                dcc.Input(id='profile-name-input', placeholder='Profilname', style={'width': '100%', 'marginBottom': '15px', 'padding': '12px', 'borderRadius': '8px'}),
                html.Div([
                    html.Label('Benachrichtigungstyp:'),
                    dcc.RadioItems(id='notification-type-radio', options=[
                        {'label': 'Whitelist', 'value': 'whitelist'},
                        {'label': 'Blacklist', 'value': 'blacklist'}
                    ], value='whitelist', inline=True)
                ], style={'marginBottom': '15px'}),
                html.Div([
                    html.Label('Benachrichtigungsmethode:'),
                    dcc.RadioItems(id='notification-method-radio', options=[
                        {'label': 'Apprise (Erweitert)', 'value': 'apprise'},
                        {'label': 'E-Mail (Einfach)', 'value': 'email'}
                    ], value='apprise', inline=True)
                ], style={'marginBottom': '15px'}),
                dcc.Textarea(id='apprise-urls-textarea', placeholder='Apprise URLs (eine pro Zeile)',
                           style={'width': '100%', 'height': '100px', 'marginBottom': '15px', 'padding': '12px', 'borderRadius': '8px', 'fontFamily': 'monospace'}),
                html.Div(id='form-error', style={'color': '#e74c3c', 'marginBottom': '15px'}),
                html.Div([
                    html.Button('Profil speichern', id='save-profile-button', n_clicks=0, style=get_button_style('success')),
                    html.Button('Abbrechen', id='cancel-profile-button', n_clicks=0, style=get_button_style('secondary'))
                ], style={'display': 'flex', 'gap': '10px'})
            ], style={'display': 'none', 'marginTop': '20px', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '12px', 'border': '1px solid #e9ecef'}),

            # Apprise test section
            html.Hr(style={'margin': '30px 0'}),
            html.H3('Apprise-Benachrichtigung testen'),
            html.P('Geben Sie eine Apprise-URL ein, um zu testen, ob Ihr Benachrichtigungssystem funktioniert.'),
            dcc.Input(id='test-apprise-url', type='text', placeholder='z.B. mmost://username:password@mattermost.example.org/channel',
                     style={'width': '100%', 'marginBottom': '15px', 'padding': '12px', 'borderRadius': '8px', 'fontFamily': 'monospace'}),
            html.Button('Benachrichtigung testen', id='test-notification-button', n_clicks=0, style=get_button_style('warning')),
            html.Div(id='test-result', style={'marginTop': '15px'})
        ], style={'display': 'none'})
    ], style={'maxWidth': '900px', 'margin': '0 auto', 'padding': '20px'})

# === SEPARATED CALLBACKS (One responsibility each) ===

# 1. UI State Management (based on auth store)
@callback(
    [Output('otp-login-container', 'style'),
     Output('otp-code-container', 'style'),
     Output('settings-container', 'style')],
    [Input('ui-state-store', 'data')]
)
def update_ui_visibility(ui_state):
    """Update UI visibility based on state store"""
    if not ui_state:
        return [{'display': 'block'}, {'display': 'none'}, {'display': 'none'}]

    login_style = {'display': 'block'} if ui_state.get('show_login') else {'display': 'none'}
    otp_style = {'display': 'block'} if ui_state.get('show_otp') else {'display': 'none'}
    settings_style = {'display': 'block'} if ui_state.get('show_settings') else {'display': 'none'}

    return [login_style, otp_style, settings_style]

# 2. OTP Request Handler
@callback(
    [Output('otp-state-store', 'data'),
     Output('otp-request-error', 'children')],
    [Input('request-otp-button', 'n_clicks')],
    [State('email-input', 'value'),
     State('otp-state-store', 'data'),
     State('ui-state-store', 'data')]
)
def handle_otp_request(n_clicks, email, otp_state, ui_state):
    """Handle OTP request (single responsibility)"""
    if not n_clicks or not email:
        return [no_update, no_update]

    try:
        # Validate email
        if '@' not in email or '.' not in email:
            return [no_update, 'Bitte geben Sie eine gültige E-Mail-Adresse ein.']

        # Call API
        import requests
        response = requests.post('http://localhost:8050/api/auth/otp/request',
                               json={'email': email}, timeout=10)

        if response.status_code == 200:
            # Success - update OTP state (UI will be updated by separate callback)
            new_otp_state = {'step': 'verify', 'email': email}
            return [new_otp_state, '']
        else:
            error_msg = response.json().get('error', 'Unbekannter Fehler') if response.content else 'Unbekannter Fehler'
            return [no_update, f'Fehler: {error_msg}']

    except Exception as e:
        return [no_update, f'Fehler beim Senden: {str(e)}']

# 3. OTP Verification Handler
@callback(
    [Output('auth-state-store', 'data'),
     Output('otp-verify-error', 'children'),
     Output('otp-code-input', 'value')],
    [Input('verify-otp-button', 'n_clicks')],
    [State('email-input', 'value'),
     State('otp-code-input', 'value')]
)
def handle_otp_verification(n_clicks, email, otp_code):
    """Handle OTP verification (single responsibility)"""
    if not n_clicks or not email or not otp_code:
        return [no_update, no_update, no_update]

    try:
        user = get_user_by_email(email)
        if not user:
            return [no_update, 'Benutzer nicht gefunden.', no_update]

        user_id = user[0]

        if is_account_locked(user_id):
            return [no_update, 'Konto ist gesperrt.', no_update]

        if validate_otp(user_id, otp_code):
            # Success - set auth state
            auth_state = {'authenticated': True, 'user_id': user_id, 'email': email}
            return [auth_state, '', '']  # Clear OTP input
        else:
            return [no_update, 'Ungültiger OTP-Code.', no_update]

    except Exception as e:
        return [no_update, f'Fehler: {str(e)}', no_update]

# 4. Auth State to UI State Bridge
@callback(
    [Output('ui-state-store', 'data'),
     Output('user-info', 'children'),
     Output('auth-status', 'data')],
    [Input('auth-state-store', 'data')],
    prevent_initial_call=True
)
def update_ui_from_auth(auth_state):
    """Update UI state when auth state changes"""
    if not auth_state or not auth_state.get('authenticated'):
        ui_state = {'show_login': True, 'show_otp': False, 'show_settings': False}
        return [ui_state, '', {'authenticated': False}]

    # Authenticated - show settings
    email = auth_state.get('email', 'Unbekannt')
    ui_state = {'show_login': False, 'show_otp': False, 'show_settings': True}
    user_info = html.Div([
        html.Span(f'Eingeloggt als: {email}', style={'fontWeight': '500'}),
        html.Button('Abmelden', id='logout-button-integrated', n_clicks=0, style=get_button_style('secondary'))
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})

    return [ui_state, user_info, auth_state]

# 5. OTP State to UI State Bridge
@callback(
    Output('ui-state-store', 'data', allow_duplicate=True),
    [Input('otp-state-store', 'data')],
    prevent_initial_call=True
)
def update_ui_from_otp(otp_state):
    """Update UI when OTP state changes"""
    if not otp_state:
        return {'show_login': True, 'show_otp': False, 'show_settings': False}

    if otp_state.get('step') == 'verify':
        return {'show_login': False, 'show_otp': True, 'show_settings': False}

    return {'show_login': True, 'show_otp': False, 'show_settings': False}

# 6. Logout Handler
@callback(
    Output('auth-state-store', 'data', allow_duplicate=True),
    [Input('logout-button', 'n_clicks'),
     Input('logout-button-integrated', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(logout_clicks, logout_integrated_clicks):
    """Handle logout (single responsibility)"""
    if not logout_clicks and not logout_integrated_clicks:
        return no_update

    # Reset auth state
    return {'authenticated': False, 'user_id': None, 'email': None}

# 7. Apprise Test Handler
@callback(
    Output('test-result', 'children'),
    [Input('test-notification-button', 'n_clicks')],
    [State('test-apprise-url', 'value'),
     State('auth-state-store', 'data')],
    prevent_initial_call=True
)
def test_apprise_notification(n_clicks, apprise_url, auth_state):
    """Test Apprise notification (single responsibility)"""
    if not n_clicks:
        return no_update

    if not auth_state or not auth_state.get('authenticated'):
        return html.Div('Authentifizierung erforderlich.', style={'color': 'red'})

    if not apprise_url or not apprise_url.strip():
        return html.Div('Bitte geben Sie eine Apprise-URL zum Testen ein.', style={'color': 'orange'})

    try:
        # Test the URL
        apobj = apprise.Apprise()
        if not apobj.add(apprise_url.strip()):
            return html.Div('Ungültiges Apprise-URL-Format.', style={'color': 'red'})

        result = apobj.notify(
            title='TI-Monitoring Test-Benachrichtigung',
            body='Dies ist eine Test-Benachrichtigung. Wenn Sie diese erhalten, funktioniert Ihre Konfiguration!',
            body_format=apprise.NotifyFormat.TEXT
        )

        if result:
            return html.Div('✅ Test-Benachrichtigung erfolgreich gesendet!', style={'color': 'green'})
        else:
            return html.Div('❌ Test-Benachrichtigung konnte nicht gesendet werden.', style={'color': 'red'})

    except Exception as e:
        return html.Div(f'❌ Fehler: {str(e)}', style={'color': 'red'})

# 8. Profile Form Toggle
@callback(
    Output('profile-form-container', 'style'),
    [Input('add-profile-button', 'n_clicks'),
     Input('cancel-profile-button', 'n_clicks')],
    prevent_initial_call=True
)
def toggle_profile_form(add_clicks, cancel_clicks):
    """Show/hide profile form"""
    ctx = callback_context
    if not ctx.triggered:
        return {'display': 'none'}

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'add-profile-button' and add_clicks:
        return {'display': 'block', 'marginTop': '20px', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '12px', 'border': '1px solid #e9ecef'}
    elif trigger_id == 'cancel-profile-button' and cancel_clicks:
        return {'display': 'none'}

    return {'display': 'none'}

# 9. Profile Save Handler
@callback(
    [Output('form-error', 'children'),
     Output('profile-name-input', 'value'),
     Output('apprise-urls-textarea', 'value')],
    [Input('save-profile-button', 'n_clicks')],
    [State('profile-name-input', 'value'),
     State('notification-type-radio', 'value'),
     State('notification-method-radio', 'value'),
     State('apprise-urls-textarea', 'value'),
     State('auth-state-store', 'data')],
    prevent_initial_call=True
)
def save_profile(n_clicks, name, notification_type, notification_method, apprise_urls, auth_state):
    """Save profile (single responsibility)"""
    if not n_clicks:
        return [no_update, no_update, no_update]

    if not auth_state or not auth_state.get('authenticated'):
        return ['Nicht authentifiziert.', no_update, no_update]

    if not name or not name.strip():
        return ['Profilname ist erforderlich.', no_update, no_update]

    try:
        user_id = auth_state.get('user_id')
        email_notifications = notification_method == 'email'
        email_address = auth_state.get('email') if email_notifications else None

        # Process Apprise URLs
        url_items = []
        if notification_method == 'apprise' and apprise_urls:
            url_items = [url.strip() for url in apprise_urls.split('\n') if url.strip()]
            if url_items and not validate_apprise_urls(url_items):
                return ['Eine oder mehrere Apprise-URLs sind ungültig.', no_update, no_update]

        # Save profile (simplified - no CI selection for now)
        profile_id = create_notification_profile(user_id, name, notification_type, [], url_items, email_notifications, email_address)

        if profile_id:
            return ['✅ Profil erfolgreich erstellt!', '', '']  # Clear form
        else:
            return ['Fehler beim Erstellen des Profils.', no_update, no_update]

    except Exception as e:
        return [f'Fehler: {str(e)}', no_update, no_update]

# Register page at the end
try:
    dash.register_page(__name__, path='/notifications')
except:
    pass

layout = serve_layout
