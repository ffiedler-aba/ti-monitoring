import dash
from dash import html, dcc, Input, Output, State, callback, no_update, callback_context
import json
from mylibrary import *
import yaml
import os
import apprise
import secrets
from datetime import datetime

# Modern button styles
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

# Hover effects for buttons
def get_button_style(button_type='primary'):
    base_style = MODERN_BUTTON_STYLES[button_type].copy()
    return base_style

# Error div styles
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
    if visible:
        base_style['display'] = 'block'
    else:
        base_style['display'] = 'none'
    return base_style

def load_config():
    """Load configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def load_core_config():
    """Load core configuration from YAML file"""
    config = load_config()
    return config.get('core', {})

dash.register_page(__name__, path='/notifications')

def serve_layout():
    layout = html.Div([
        html.H2('Benachrichtigungseinstellungen', style={
            'color': '#2c3e50',
            'fontWeight': '600',
            'marginBottom': '30px',
            'borderBottom': '2px solid #3498db',
            'paddingBottom': '10px'
        }),
        # Store for authentication status (persistent in browser)
        # Don't set initial data - let the browser's localStorage handle persistence
        dcc.Store(id='auth-status', storage_type='local'),
        # UI state store (single source of truth for styles/content)
        dcc.Store(id='ui-state-store'),

        # OTP Login form (shown when not authenticated)
        html.Div(id='otp-login-container', children=[
            html.H3('OTP-Anmeldung erforderlich', style={'color': '#2c3e50', 'marginBottom': '20px'}),
            html.P('Bitte geben Sie Ihre E-Mail-Adresse ein, um einen OTP-Code zu erhalten.', style={'color': '#7f8c8d', 'marginBottom': '20px'}),
            dcc.Input(
                id='email-input',
                type='email',
                placeholder='E-Mail-Adresse eingeben',
                style={
                    'width': '100%',
                    'marginBottom': '15px',
                    'padding': 'clamp(8px, 2vw, 12px)',
                    'border': '2px solid #e9ecef',
                    'borderRadius': '8px',
                    'fontSize': 'clamp(12px, 2.5vw, 14px)',
                    'transition': 'border-color 0.3s ease',
                    'boxSizing': 'border-box'
                }
            ),
            html.Button('OTP anfordern', id='request-otp-button', n_clicks=0, style=get_button_style('primary')),
            html.Div(id='otp-request-error', style={'color': '#e74c3c', 'marginTop': '15px', 'fontWeight': '500'})
        ], style={
            'width': '100%',
            'maxWidth': '900px',
            'margin': '0 auto',
            'padding': 'clamp(20px, 4vw, 30px)',
            'backgroundColor': 'white',
            'borderRadius': '12px',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
            'boxSizing': 'border-box'
        }),

        # OTP Code form (shown after email is entered)
        html.Div(id='otp-code-container', children=[
            html.H3('OTP-Code eingeben', style={'color': '#2c3e50', 'marginBottom': '20px'}),
            html.P(id='otp-instructions', children='Bitte geben Sie den 6-stelligen Code ein, den Sie per E-Mail erhalten haben.', style={'color': '#7f8c8d', 'marginBottom': '20px'}),
            dcc.Input(
                id='otp-code-input',
                type='text',
                placeholder='6-stelliger Code',
                style={
                    'width': '100%',
                    'marginBottom': '15px',
                    'padding': 'clamp(8px, 2vw, 12px)',
                    'border': '2px solid #e9ecef',
                    'borderRadius': '8px',
                    'fontSize': 'clamp(12px, 2.5vw, 14px)',
                    'transition': 'border-color 0.3s ease',
                    'boxSizing': 'border-box'
                }
            ),
            html.Button('Anmelden', id='verify-otp-button', n_clicks=0, style=get_button_style('primary')),
            html.Button('Neuen Code anfordern', id='resend-otp-button', n_clicks=0, style=get_button_style('secondary')),
            html.Div(id='otp-verify-error', style={'color': '#e74c3c', 'marginTop': '15px', 'fontWeight': '500'})
        ], style={
            'width': '100%',
            'maxWidth': '900px',
            'margin': '0 auto',
            'padding': 'clamp(20px, 4vw, 30px)',
            'backgroundColor': 'white',
            'borderRadius': '12px',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
            'boxSizing': 'border-box',
            'display': 'none'
        }),

        # Settings interface (hidden when not authenticated)
        html.Div(id='settings-container', children=[
            html.Div(id='user-info', style={
                'marginBottom': '20px',
                'padding': '15px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '8px',
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center'
            }),


            # Delete profile button + confirm dialog
            html.Button('Profil vollständig löschen', id='delete-own-profile-button', n_clicks=0, style={
                **get_button_style('danger'),
                'marginLeft': '10px'
            }),
            dcc.ConfirmDialog(id='confirm-delete-user-profile', message='Soll Ihr Profil (alle Benachrichtigungen) endgültig gelöscht werden?'),

            # Status message for delete operations
            html.Div(id='delete-status-message', style={'color': '#e74c3c', 'marginTop': '15px', 'fontWeight': '500'}),

            html.P('Verwalten Sie Ihre Benachrichtigungsprofile unten.', style={
                'color': '#7f8c8d',
                'fontSize': '16px',
                'marginBottom': '25px'
            }),

            # Display existing profiles
            html.Div(id='profiles-container'),

            # Add new profile button
            html.Button('Neues Profil hinzufügen', id='add-profile-button', n_clicks=0, style=get_button_style('success')),

            # Profile form (hidden by default)
            html.Div(id='profile-form-container', children=[
                html.H3('Profildetails', style={
                    'color': '#2c3e50',
                    'marginBottom': '20px',
                    'borderBottom': '2px solid #3498db',
                    'paddingBottom': '10px'
                }),
                dcc.Store(id='editing-profile-index'),
                dcc.Store(id='editing-profile-id'),
                dcc.Store(id='available-cis-data'),
                dcc.Store(id='selected-cis-data', data=[]),
                dcc.Store(id='ci-filter-text', data=''),
                dcc.Input(
                    id='profile-name-input',
                    placeholder='Profilname',
                    style={
                        'width': '100%',
                        'marginBottom': '15px',
                        'padding': '12px',
                        'border': '2px solid #e9ecef',
                        'borderRadius': '8px',
                        'fontSize': '14px',
                        'transition': 'border-color 0.3s ease',
                        'boxSizing': 'border-box'
                    }
                ),
                html.Div([
                    html.Label('Benachrichtigungstyp:', style={
                        'display': 'block',
                        'marginBottom': '10px',
                        'fontWeight': '500',
                        'color': '#2c3e50'
                    }),
                    dcc.RadioItems(
                        id='notification-type-radio',
                        options=[
                            {'label': 'Whitelist', 'value': 'whitelist'},
                            {'label': 'Blacklist', 'value': 'blacklist'}
                        ],
                        value='whitelist',
                        inline=True,
                        style={
                            'marginBottom': '15px',
                            'width': '100%',
                            'display': 'flex',
                            'gap': '20px'
                        }
                    )
                ], style={
                    'marginBottom': '15px',
                    'width': '100%'
                }),
                html.Div([
                    html.Label('Konfigurationsobjekte:', style={
                        'display': 'block',
                        'marginBottom': '10px',
                        'fontWeight': '500',
                        'color': '#2c3e50'
                    }),
                    html.Div([
                        dcc.Input(
                            id='ci-filter-input',
                            type='text',
                            placeholder='CIs filtern (z.B. "CI-0000" oder "gematik")',
                            style={
                                'flex': '1',
                                'minWidth': '0',
                                'padding': '8px 12px',
                                'border': '2px solid #e9ecef',
                                'borderRadius': '6px',
                                'fontSize': '14px',
                                'marginRight': '10px',
                                'transition': 'border-color 0.3s ease',
                                'boxSizing': 'border-box'
                            }
                        ),
                        html.Button('Alle aktivieren', id='select-all-cis-button', n_clicks=0, style=get_button_style('secondary')),
                        html.Button('Alle deaktivieren', id='deselect-all-cis-button', n_clicks=0, style=get_button_style('secondary'))
                    ], style={
                        'display': 'flex',
                        'gap': '10px',
                        'marginBottom': '10px',
                        'alignItems': 'center',
                        'width': '100%',
                        'boxSizing': 'border-box'
                    }),
                    html.Div(id='ci-filter-info', style={
                        'width': '100%',
                        'fontSize': '12px',
                        'color': '#7f8c8d',
                        'marginBottom': '8px',
                        'fontStyle': 'italic'
                    }),
                    html.Div(id='ci-checkboxes-container', style={
                        'width': '100%',
                        'maxHeight': '200px',
                        'overflowY': 'auto',
                        'border': '2px solid #e9ecef',
                        'borderRadius': '8px',
                        'padding': '15px',
                        'backgroundColor': '#f8f9fa',
                        'boxSizing': 'border-box'
                    })
                ], style={
                    'marginBottom': '15px',
                    'width': '100%'
                }),
                html.Div([
                    html.Label('Benachrichtigungsmethode:', style={
                        'display': 'block',
                        'marginBottom': '10px',
                        'fontWeight': '500',
                        'color': '#2c3e50'
                    }),
                    dcc.RadioItems(
                        id='notification-method-radio',
                        options=[
                            {'label': 'Apprise (Erweitert)', 'value': 'apprise'},
                            {'label': 'E-Mail (Einfach)', 'value': 'email'}
                        ],
                        value='apprise',
                        inline=True,
                        style={
                            'marginBottom': '15px',
                            'width': '100%',
                            'display': 'flex',
                            'gap': '20px'
                        }
                    )
                ], style={
                    'marginBottom': '15px',
                    'width': '100%'
                }),
                html.Div(id='apprise-section', children=[
                    dcc.Textarea(
                        id='apprise-urls-textarea',
                        placeholder='Apprise URLs (eine pro Zeile)',
                        style={
                            'width': '100%',
                            'height': '100px',
                            'marginBottom': '15px',
                            'padding': '12px',
                            'border': '2px solid #e9ecef',
                            'borderRadius': '8px',
                            'fontSize': '14px',
                            'fontFamily': 'monospace',
                            'resize': 'vertical',
                            'transition': 'border-color 0.3s ease',
                            'boxSizing': 'border-box'
                        }
                    )
                ]),
                html.Div(id='email-section', children=[
                    html.P('Die E-Mail wird an Ihre Anmeldeadresse gesendet.', style={
                        'color': '#7f8c8d',
                        'fontSize': '14px',
                        'marginBottom': '15px'
                    })
                ], style={'display': 'none'}),
                html.Div(id='form-error', style={
                    **get_error_style(visible=False),
                    'width': '100%'
                }),
                html.Div([
                    html.Button('Profil speichern', id='save-profile-button', n_clicks=0, style=get_button_style('success')),
                    html.Button('Abbrechen', id='cancel-profile-button', n_clicks=0, style=get_button_style('secondary'))
                ], style={
                    'display': 'flex',
                    'gap': '10px',
                    'justifyContent': 'flex-end',
                    'width': '100%'
                })
            ], style={
                'display': 'none',
                'width': '100%',
                'backgroundColor': 'white',
                'padding': 'clamp(15px, 3vw, 25px)',
                'borderRadius': '12px',
                'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                'marginTop': '20px',
                'border': '1px solid #e9ecef'
            }),

            # Delete confirmation modal
            dcc.ConfirmDialog(
                id='delete-confirm',
                message='Sind Sie sicher, dass Sie dieses Profil löschen möchten?'
            ),

            # Store for delete index
            dcc.Store(id='delete-index-store', data=None),

            # Stores for select/deselect all triggers
            dcc.Store(id='select-all-trigger', data=None),
            dcc.Store(id='deselect-all-trigger', data=None),
            # Test Apprise notification button
            html.Div([
                html.H3('Apprise-Benachrichtigung testen', style={
                    'color': '#2c3e50',
                    'marginBottom': '15px',
                    'borderBottom': '2px solid #3498db',
                    'paddingBottom': '10px'
                }),
                html.P('Geben Sie eine Apprise-URL ein, um zu testen, ob Ihr Benachrichtigungssystem funktioniert.', style={
                    'color': '#7f8c8d',
                    'marginBottom': '15px'
                }),
                dcc.Input(
                    id='test-apprise-url',
                    type='text',
                    placeholder='e.g., mmost://username:password@mattermost.medisoftware.org/channel',
                    style={
                        'width': '100%',
                        'marginBottom': '15px',
                        'padding': '12px',
                        'border': '2px solid #e9ecef',
                        'borderRadius': '8px',
                        'fontSize': '14px',
                        'fontFamily': 'monospace',
                        'transition': 'border-color 0.3s ease',
                        'boxSizing': 'border-box'
                    }
                ),
                html.Button('Benachrichtigung testen', id='test-notification-button', n_clicks=0, style=get_button_style('warning')),
                html.Div(id='test-result', style={
                    'width': '100%',
                    'marginTop': '15px'
                })
            ], style={
                'width': '100%',
                'marginTop': '30px',
                'padding': 'clamp(15px, 3vw, 25px)',
                'border': '1px solid #e9ecef',
                'borderRadius': '12px',
                'backgroundColor': 'white',
                'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
            })
        ], style={'display': 'none'})
        ], style={
            'width': '100%',
            'maxWidth': '900px',
            'minWidth': '320px',
            'margin': '0 auto',
            'padding': 'clamp(10px, 3vw, 20px)',
            'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
            'boxSizing': 'border-box'
        })

    return layout

layout = serve_layout

# Callback: Confirm-Dialog für Profil-Löschung anzeigen
@callback(
    Output('confirm-delete-user-profile', 'displayed'),
    [Input('delete-own-profile-button', 'n_clicks')],
    [State('auth-status', 'data')],
    prevent_initial_call=True
)
def show_delete_confirm_dialog(n_clicks, auth_data):
    if not n_clicks:
        return no_update
    if not auth_data or not auth_data.get('authenticated'):
        return no_update
    return True

# Callback: Profil löschen nach Bestätigung
@callback(
    Output('delete-status-message', 'children'),
    [Input('confirm-delete-user-profile', 'submit_n_clicks')],
    [State('auth-status', 'data')],
    prevent_initial_call=True
)
def delete_user_profile(confirm_clicks, auth_data):
    if not confirm_clicks:
        return no_update
    try:
        if not auth_data or not auth_data.get('authenticated'):
            return no_update
        user_email = auth_data.get('email')
        if not user_email:
            return no_update

        # Use get_user_by_email which handles encryption correctly
        user_data = get_user_by_email(user_email)
        if user_data:
            user_id = user_data[0]
            with get_db_conn() as conn, conn.cursor() as cur:
                # Delete all related data first
                cur.execute("DELETE FROM notification_profiles WHERE user_id=%s", (user_id,))
                cur.execute("DELETE FROM sessions WHERE user_id=%s", (user_id,))
                cur.execute("DELETE FROM user_otps WHERE user_id=%s", (user_id,))
                cur.execute("DELETE FROM otp_codes WHERE user_id=%s", (user_id,))
                # Delete user completely
                cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
                conn.commit()

        # Return success message (auth reset happens via page reload)
        return 'Ihr Profil wurde vollständig gelöscht. Seite wird neu geladen...'
    except Exception as e:
        return f'Fehler beim Löschen: {str(e)}'

# Consolidated callback for authentication state management
@callback(
    [Output('otp-login-container', 'style'),
     Output('settings-container', 'style'),
     Output('otp-code-container', 'style'),
     Output('user-info', 'children'),
     Output('logout-button', 'style'),
     Output('otp-request-error', 'children'),
     Output('otp-instructions', 'children'),
     Output('otp-verify-error', 'children'),
     Output('auth-status', 'data'),
     Output('email-input', 'value'),
     Output('otp-code-input', 'value')],
    [Input('auth-status', 'data'),
     Input('request-otp-button', 'n_clicks'),
     Input('verify-otp-button', 'n_clicks'),
     Input('resend-otp-button', 'n_clicks'),
     Input('logout-button', 'n_clicks')],
    [State('email-input', 'value'),
     State('otp-code-input', 'value')],
    prevent_initial_call=True
)
def manage_authentication_state(auth_data, otp_clicks, verify_clicks, resend_clicks, logout_clicks, email, otp_code):
    """Consolidated callback for authentication state management"""
    ctx = dash.callback_context

    # Handle logout
    if ctx.triggered and 'logout-button' in ctx.triggered[0]['prop_id']:
        if logout_clicks and logout_clicks > 0:
            # Reset authentication status
            auth_data = {'authenticated': False, 'user_id': None, 'email': None}
            return [
                {'display': 'block'},  # Show login container
                {'display': 'none'},   # Hide settings container
                {'display': 'none'},   # Hide OTP code container
                '',  # No user info
                {'display': 'none'},  # Hide logout button
                '',  # Clear request error
                '',  # Clear instructions
                '',  # Clear verify error
                auth_data,  # Reset auth data
                '',  # Clear email input
                ''   # Clear OTP input
            ]

    # Handle OTP verification
    if ctx.triggered and 'verify-otp-button' in ctx.triggered[0]['prop_id']:
        if verify_clicks and verify_clicks > 0:
            if not email or not otp_code:
                return [
                    no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update,
                    'Bitte geben Sie E-Mail und OTP-Code ein.',
                    no_update, no_update, no_update
                ]

        try:
            # Get user by email
            user = get_user_by_email(email)
            if not user:
                return [
                    no_update, no_update, no_update, no_update,
                    no_update, no_update,
                    'Benutzer nicht gefunden.',
                    no_update, no_update, no_update
                ]

            user_id = user[0]

            # Check if account is locked
            if is_account_locked(user_id):
                return [
                    no_update, no_update, no_update, no_update,
                    no_update, no_update,
                    'Konto ist gesperrt. Bitte versuchen Sie es später erneut.',
                    no_update, no_update, no_update
                ]

            # Validate OTP
            if validate_otp(user_id, otp_code):
                # Authentication successful
                if not auth_data:
                    auth_data = {}
                auth_data['authenticated'] = True
                auth_data['user_id'] = user_id
                auth_data['email'] = email

                # Create user info with integrated logout button
                user_info = html.Div([
                    html.Span(f'Eingeloggt als: {email}', style={'fontWeight': '500'}),
                    html.Button('Abmelden', id='logout-button', n_clicks=0, style=get_button_style('secondary'))
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})

                return [
                    {'display': 'none'},  # Hide login container
                    {'display': 'block'}, # Show settings container
                    {'display': 'none'},  # Hide OTP code container
                    user_info,  # Show user info with integrated logout button
                    {'display': 'none'},  # Logout button is integrated in user_info
                    '',  # Clear request error
                    '',  # Clear instructions
                    '',  # Clear verify error
                    auth_data,  # Update auth data
                    email,  # Keep email
                    ''  # Clear OTP input
                ]
            else:
                # OTP validation failed
                return [
                    no_update, no_update, no_update, no_update,
                    no_update, no_update,
                    'Ungültiger OTP-Code. Bitte versuchen Sie es erneut.',
                    no_update, no_update, no_update
                ]

        except Exception as e:
            return [
                no_update, no_update, no_update, no_update,
                no_update, no_update,
                f'Fehler bei der OTP-Verifikation: {str(e)}',
                no_update, no_update, no_update
            ]

    # Handle resend OTP
    if ctx.triggered and 'resend-otp-button' in ctx.triggered[0]['prop_id']:
        if resend_clicks and resend_clicks > 0:
            if not email:
                return [
                    no_update, no_update, no_update, no_update, no_update,
                    'Bitte geben Sie eine E-Mail-Adresse ein.',
                    no_update, no_update,
                    no_update, no_update, no_update
                ]

            try:
                # Get user by email
                user = get_user_by_email(email)
                if not user:
                    return [
                        no_update, no_update, no_update, no_update, no_update,
                        'Benutzer nicht gefunden.',
                        no_update, no_update,
                        no_update, no_update, no_update
                    ]

                user_id = user[0]

                # Generate new OTP
                otp, otp_id = generate_otp_for_user(user_id, None)

                # Send OTP via Apprise (using the template from config)
                config = load_config()
                if not config:
                    return [no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update]
                otp_template = config.get('core', {}).get('otp_apprise_url_template')

                if otp_template:
                    # Format the template with user email and OTP
                    apprise_url = otp_template.format(email=email, otp=otp)

                    # Send OTP notification
                    apobj = apprise.Apprise()
                    apobj.add(apprise_url)
                    apobj.notify(
                        title='TI-Monitoring OTP-Code (erneut gesendet)',
                        body=f'Ihr neuer OTP-Code für TI-Monitoring lautet: {otp}\n\nDieser Code ist 10 Minuten gültig.',
                        body_format=apprise.NotifyFormat.TEXT
                    )

                return [
                    no_update, no_update, no_update, no_update, no_update,
                    f'Neuer OTP-Code wurde an {email} gesendet.',
                    no_update, no_update,
                    no_update, no_update, no_update
                ]

            except Exception as e:
                return [
                    no_update, no_update, no_update, no_update, no_update,
                    f'Fehler beim erneuten Senden des OTP-Codes: {str(e)}',
                    no_update, no_update,
                    no_update, no_update, no_update
                ]

    # Handle OTP request
    if ctx.triggered and 'request-otp-button' in ctx.triggered[0]['prop_id']:
        if otp_clicks and otp_clicks > 0:
            if not email:
                return [
                    no_update, no_update, no_update, no_update, no_update,
                    'Bitte geben Sie eine E-Mail-Adresse ein.',
                    no_update, no_update,
                    no_update, no_update, no_update
                ]

            try:
                # Validate email format
                if '@' not in email or '.' not in email:
                    return [
                        no_update, no_update, no_update, no_update, no_update,
                        'Bitte geben Sie eine gültige E-Mail-Adresse ein.',
                        no_update, no_update,
                        no_update, no_update, no_update
                    ]

                # Check if user exists, create if not
                user = get_user_by_email(email)
                if user:
                    user_id = user[0]
                else:
                    user_id = create_user(email)

                if not user_id:
                    return [
                        no_update, no_update, no_update, no_update, no_update,
                        'Fehler beim Erstellen des Benutzers.',
                        no_update, no_update,
                        no_update, no_update, no_update
                    ]

                # Generate OTP
                otp, otp_id = generate_otp_for_user(user_id, None)
                if not otp or not otp_id:
                    return [
                        no_update, no_update, no_update, no_update, no_update,
                        'Fehler beim Generieren des OTP-Codes.',
                        no_update, no_update,
                        no_update, no_update, no_update
                    ]

                # Send OTP via Apprise
                try:
                    import requests
                    response = requests.post('http://localhost:8050/api/auth/otp/request',
                                           json={'email': email}, timeout=10)
                    if response.status_code == 200:
                        return [
                            {'display': 'none'},  # Hide login container
                            {'display': 'none'},  # Hide settings container
                            {'display': 'block'}, # Show OTP code container
                            '',  # No user info
                            {**get_button_style('secondary'), 'display': 'none'},  # Hide logout button with proper styling
                            '',  # Clear request error
                            f'OTP-Code wurde an {email} gesendet. Bitte geben Sie den Code ein.',
                            '',  # Clear verify error
                            no_update,  # Keep auth data
                            email,  # Keep email
                            ''  # Clear OTP input
                        ]
                    else:
                        try:
                            response_data = response.json()
                            error_msg = response_data.get('error', 'Unbekannter Fehler') if response_data else 'Unbekannter Fehler'
                        except:
                            error_msg = 'Unbekannter Fehler'
                        return [
                            no_update, no_update, no_update, no_update, no_update,
                            f'Fehler beim Senden des OTP-Codes: {error_msg}',
                            no_update, no_update,
                            no_update, no_update, no_update
                        ]
                except Exception as e:
                    return [
                        no_update, no_update, no_update, no_update, no_update,
                        f'Fehler beim Senden des OTP-Codes: {str(e)}',
                        no_update, no_update,
                        no_update, no_update, no_update
                    ]

            except Exception as e:
                return [
                    no_update, no_update, no_update, no_update, no_update,
                    f'Fehler: {str(e)}',
                    no_update, no_update,
                    no_update, no_update, no_update
                ]

    # Handle initial load or auth status change
    if not auth_data:
        # No auth data - show login form
        return [
            {'display': 'block'},  # Show login container
            {'display': 'none'},   # Hide settings container
            {'display': 'none'},   # Hide OTP code container
            '',  # No user info
            {**get_button_style('secondary'), 'display': 'none'},  # Hide logout button with proper styling
            '',  # Clear request error
            '',  # Clear instructions
            '',  # Clear verify error
            no_update,  # Keep auth data
            no_update,  # Keep email
            no_update   # Keep OTP
        ]

    if auth_data.get('authenticated', False):
        # User is authenticated - show settings
        email = auth_data.get('email', 'Unbekannt')
        user_info = html.Div([
            html.Span(f'Eingeloggt als: {email}', style={'fontWeight': '500'}),
            html.Button('Abmelden', id='logout-button', n_clicks=0, style=get_button_style('secondary'))
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})

        return [
            {'display': 'none'},  # Hide login container
            {'display': 'block'}, # Show settings container
            {'display': 'none'},  # Hide OTP code container
            user_info,  # Show user info with integrated logout button
            {'display': 'none'},  # Logout button is integrated in user_info
            '',  # Clear request error
            '',  # Clear instructions
            '',  # Clear verify error
            no_update,  # Keep auth data
            no_update,  # Keep email
            no_update   # Keep OTP
        ]
    else:
        # User is not authenticated - show login form
        return [
            {'display': 'block'},  # Show login container
            {'display': 'none'},   # Hide settings container
            {'display': 'none'},   # Hide OTP code container
            '',  # No user info
            {'display': 'none'},  # Hide logout button
            '',  # Clear request error
            '',  # Clear instructions
            '',  # Clear verify error
            no_update,  # Keep auth data
            no_update,  # Keep email
            no_update   # Keep OTP
        ]

# Initial load callback removed - consolidated into manage_authentication_state

# OTP request callback removed - consolidated into manage_authentication_state

# Derive minimal UI state into dcc.Store for future refactor (non-invasive)
@callback(
    Output('ui-state-store', 'data'),
    [Input('auth-status', 'data')],
    [State('email-input', 'value')],
    prevent_initial_call=False
)
def derive_ui_state(auth_data, email):
    state = {
        'showLogin': True,
        'showSettings': False,
        'showOtp': False,
        'email': email or ''
    }
    try:
        if auth_data and auth_data.get('authenticated'):
            state['showLogin'] = False
            state['showSettings'] = True
            state['email'] = auth_data.get('email', state['email'])
    except Exception:
        pass
    return state

# OTP verification callback removed - consolidated into manage_authentication_state

# Resend OTP callback removed - consolidated into manage_authentication_state

# Callback to handle Enter key in password input
@callback(
    Output('verify-otp-button', 'n_clicks'),
    [Input('otp-code-input', 'n_submit')],
    [State('verify-otp-button', 'n_clicks')]
)
def handle_enter_key(n_submit, current_clicks):
    if n_submit and n_submit > 0:
        return (current_clicks or 0) + 1
    return current_clicks

# Callback to load all available CIs
@callback(
    Output('available-cis-data', 'data'),
    [Input('auth-status', 'data')]
)
def load_available_cis(auth_data):
    if not auth_data or not auth_data.get('authenticated', False):
        return []

    try:
        # Try to load CIs from the JSON file first (faster)
        ci_list_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ci_list.json')

        if os.path.exists(ci_list_file_path):
            try:
                with open(ci_list_file_path, 'r', encoding='utf-8') as f:
                    ci_list = json.load(f)
                print(f"Loaded {len(ci_list)} CIs from JSON file")
                return ci_list
            except Exception as e:
                print(f"Error loading from JSON file: {e}, falling back to TimescaleDB")

        # Fallback: Load from TimescaleDB if JSON doesn't exist or fails
        from mylibrary import get_data_of_all_cis
        cis_df = get_data_of_all_cis('')  # file_name parameter not used anymore

        if not cis_df.empty:
            # Convert to list of dictionaries with ci and name
            ci_list = []
            for _, row in cis_df.iterrows():
                if row is not None:
                    ci_info = {
                        'ci': str(row.get('ci', '')),
                        'name': str(row.get('name', '')),
                        'organization': str(row.get('organization', '')),
                        'product': str(row.get('product', ''))
                    }
                else:
                    continue
                ci_list.append(ci_info)
            return ci_list
        else:
            return []
    except Exception as e:
        print(f"Error loading CIs: {e}")
        return []

# Callback to render CI checkboxes (consolidated)
@callback(
    Output('ci-checkboxes-container', 'children'),
    [Input('available-cis-data', 'data'),
     Input('editing-profile-index', 'data'),
     Input('ci-filter-text', 'data'),
     Input('selected-cis-data', 'data')],
    [State('auth-status', 'data')]
)
def render_ci_checkboxes(cis_data, editing_index, filter_text, selected_cis, auth_data):
    if not auth_data or not auth_data.get('authenticated', False) or not cis_data:
        return html.P('Loading CIs...', style={'color': '#7f8c8d', 'textAlign': 'center'})

    try:
        # Load existing profile data if editing
        selected_cis = []
        if editing_index is not None:
            # editing_index is now the profile_id from the database
            with get_db_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT ci_list FROM notification_profiles WHERE id = %s
                """, (editing_index,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    selected_cis = result[0]
                    print(f"DEBUG: render_ci_checkboxes - loaded selected_cis: {selected_cis}, type: {type(selected_cis)}")
                else:
                    selected_cis = []  # Ensure it's an empty list if None
                    print(f"DEBUG: render_ci_checkboxes - no result or None, using empty list")

        # Filter CIs based on filter text
        filtered_cis = []
        if filter_text and filter_text.strip():
            filter_lower = filter_text.lower().strip()
            for ci_info in cis_data:
                ci_id = ci_info.get('ci', '').lower()
                ci_name = ci_info.get('name', '').lower()
                ci_org = ci_info.get('organization', '').lower()
                ci_product = ci_info.get('product', '').lower()

                # Check if any field contains the filter text
                if (filter_lower in ci_id or
                    filter_lower in ci_name or
                    filter_lower in ci_org or
                    filter_lower in ci_product):
                    filtered_cis.append(ci_info)
        else:
            # No filter, show all CIs
            filtered_cis = cis_data

        # Create checkboxes for each filtered CI
        checkbox_children = []
        for ci_info in filtered_cis:
            if ci_info is not None:
                ci_id = ci_info.get('ci', '')
                ci_name = ci_info.get('name', '')
                ci_org = ci_info.get('organization', '')
                ci_product = ci_info.get('product', '')
            else:
                continue

            # Check if this CI is selected
            is_checked = ci_id in selected_cis

            # Create checkbox with label
            checkbox = html.Div([
                dcc.Checklist(
                    id={'type': 'ci-checkbox', 'ci': ci_id},
                    options=[{'label': '', 'value': ci_id}],
                    value=[ci_id] if is_checked else [],
                    style={'marginRight': '10px'}
                ),
                html.Label([
                    html.Strong(ci_id),
                    html.Br(),
                    html.Span(f"{ci_name}", style={'color': '#2c3e50', 'fontSize': '14px'}),
                    html.Br(),
                    html.Span(f"{ci_org} - {ci_product}", style={'color': '#7f8c8d', 'fontSize': '12px'})
                ], style={'cursor': 'pointer', 'marginLeft': '5px'})
            ], style={
                'display': 'flex',
                'alignItems': 'flex-start',
                'marginBottom': '10px',
                'padding': '8px',
                'borderRadius': '6px',
                'backgroundColor': 'white',
                'border': '1px solid #e9ecef'
            })

            checkbox_children.append(checkbox)

        if not checkbox_children:
            return html.P('No CIs found', style={'color': '#7f8c8d', 'textAlign': 'center'})

        return checkbox_children

    except Exception as e:
        return html.P(f'Error loading CIs: {str(e)}', style={'color': '#e74c3c', 'textAlign': 'center'})

# Callback to reset selected CIs when form is opened/closed
@callback(
    Output('selected-cis-reset-trigger', 'data'),
    [Input('profile-form-container', 'style')],
    [State('editing-profile-index', 'data')],
    prevent_initial_call=True
)
def reset_selected_cis(form_style, editing_index):
    """Reset selected CIs when form is opened or closed"""
    if form_style and form_style.get('display') == 'none':
        # Form is closed, reset selection
        return []
    elif editing_index is not None:
        # Form is opened for editing, load existing selection from database
        try:
            with get_db_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT ci_list FROM notification_profiles WHERE id = %s
                """, (editing_index,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    return result[0]
                else:
                    return []  # Ensure it's an empty list if None
        except Exception:
            pass
    return []

# Callback to select all CIs
@callback(
    Output('select-all-trigger', 'data'),
    [Input('select-all-cis-button', 'n_clicks')],
    [State('available-cis-data', 'data')],
    prevent_initial_call=True
)
def select_all_cis(n_clicks, available_cis_data):
    """Trigger select all CIs"""
    if not n_clicks:
        return no_update
    return {'action': 'select_all', 'timestamp': str(datetime.now())}

# Callback to deselect all CIs
@callback(
    Output('deselect-all-trigger', 'data'),
    [Input('deselect-all-cis-button', 'n_clicks')],
    prevent_initial_call=True
)
def deselect_all_cis(n_clicks):
    """Deselect all CIs"""
    if not n_clicks:
        return no_update

    # Return empty list to deselect all
    return []

# Callback to store filter text
@callback(
    Output('ci-filter-text', 'data'),
    [Input('ci-filter-input', 'value')],
    prevent_initial_call=True
)
def update_filter_text(filter_text):
    """Store the filter text for CI filtering"""
    return filter_text or ''

# Callback to update filter info display
@callback(
    Output('ci-filter-info', 'children'),
    [Input('ci-filter-text', 'data'),
     Input('available-cis-data', 'data')]
)
def update_filter_info(filter_text, available_cis_data):
    """Update the filter information display"""
    if not available_cis_data:
        return ''

    total_cis = len(available_cis_data)

    if not filter_text or not filter_text.strip():
        return f'Zeige alle {total_cis} Configuration Items'

    # Count filtered results
    filter_lower = filter_text.lower().strip()
    filtered_count = 0
    for ci_info in available_cis_data:
        ci_id = ci_info.get('ci', '').lower()
        ci_name = ci_info.get('name', '').lower()
        ci_org = ci_info.get('organization', '').lower()
        ci_product = ci_info.get('product', '').lower()

        if (filter_lower in ci_id or
            filter_lower in ci_name or
            filter_lower in ci_org or
            filter_lower in ci_product):
            filtered_count += 1

    return f'Filter: "{filter_text}" - {filtered_count} von {total_cis} CIs angezeigt'

# Callback to handle select/deselect all triggers
@callback(
    Output('selected-cis-data', 'data'),
    [Input({'type': 'ci-checkbox', 'ci': dash.ALL}, 'value'),
     Input('select-all-trigger', 'data'),
     Input('deselect-all-trigger', 'data')],
    [State('available-cis-data', 'data'),
     State('selected-cis-data', 'data')],
    prevent_initial_call=True
)
def update_selected_cis(checkbox_values, select_all_trigger, deselect_all_trigger, available_cis_data, current_selected):
    """Update the selected CIs when checkboxes change or when select/deselect all is triggered"""
    if not available_cis_data:
        return []

    ctx = callback_context
    if not ctx.triggered:
        return current_selected or []

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Handle select all trigger
    if trigger_id == 'select-all-trigger' and select_all_trigger:
        # Select all available CIs
        return [ci['ci'] for ci in available_cis_data if ci and ci.get('ci')]

    # Handle deselect all trigger
    if trigger_id == 'deselect-all-trigger' and deselect_all_trigger:
        # Deselect all CIs
        return []

    # Handle individual checkbox changes
    if 'ci-checkbox' in trigger_id:
        # Collect all selected CIs from the checkbox values
        selected_cis = []
        for checkbox_value in checkbox_values:
            if checkbox_value:  # If checkbox has a value (is checked)
                selected_cis.extend(checkbox_value)

        # Remove duplicates
        selected_cis = list(set(selected_cis))
        return selected_cis

    return current_selected or []

# Note: update_checkbox_states logic consolidated into render_ci_checkboxes

# Logout callback removed - consolidated into manage_authentication_state

# Callback to load and display profiles from database
@callback(
    Output('profiles-container', 'children'),
    [Input('auth-status', 'data'),
     Input('save-profile-button', 'n_clicks')]
)
def display_profiles(auth_data, save_clicks):
    if not auth_data or not auth_data.get('authenticated', False):
        return []

    user_id = auth_data.get('user_id')
    if not user_id:
        return html.P('Fehler: Benutzer nicht authentifiziert.')

    try:
        # Load profiles from database
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, type, ci_list, apprise_urls, email_notifications
                FROM notification_profiles
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            profiles = cur.fetchall()

        if not profiles:
            return html.P('Keine Benachrichtigungsprofile gefunden. Fügen Sie ein neues Profil hinzu, um zu beginnen.')

        profile_cards = []
        for profile in profiles:
            profile_id, name, notification_type, ci_list, apprise_urls, email_notifications = profile

            # Count items
            ci_count = len(ci_list) if ci_list else 0
            url_count = len(apprise_urls) if apprise_urls else 0
            notification_method = 'E-Mail' if email_notifications else 'Apprise'

            card = html.Div([
                html.H4(name or 'Unbenanntes Profil', style={
                    'color': '#2c3e50',
                    'marginBottom': '15px',
                    'fontWeight': '600',
                    'borderBottom': '1px solid #ecf0f1',
                    'paddingBottom': '10px'
                }),
                html.Div([
                    html.P(f"Typ: {notification_type.title() if notification_type else 'Whitelist'}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    }),
                    html.P(f"Benachrichtigungsmethode: {notification_method}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    }),
                    html.P(f"Konfigurationsobjekte: {ci_count}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    }),
                    html.P(f"Benachrichtigungs-URLs: {url_count}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    })
                ], style={'marginBottom': '20px'}),
                html.Div([
                    html.Button('Bearbeiten', id={'type': 'edit-profile', 'profile_id': str(profile_id)}, n_clicks=0, style=get_button_style('secondary')),
                    html.Button('Löschen', id={'type': 'delete-profile', 'profile_id': str(profile_id)}, n_clicks=0,
                               style=get_button_style('danger'))
                ], style={
                    'display': 'flex',
                    'gap': '10px',
                    'justifyContent': 'flex-end',
                    'width': '100%'
                })
            ], className='profile-card', style={
                'width': '100%',
                'backgroundColor': 'white',
                'padding': 'clamp(15px, 3vw, 25px)',
                'borderRadius': '12px',
                'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.1)',
                'marginBottom': '20px',
                'border': '1px solid #e9ecef',
                'transition': 'transform 0.2s ease, box-shadow 0.2s ease'
            })

            profile_cards.append(card)

        # Wrap profile cards in a container with consistent width
        return html.Div(profile_cards, style={
            'width': '100%',
            'display': 'flex',
            'flexDirection': 'column',
            'gap': '20px'
        })
    except Exception as e:
        return html.P(f'Fehler beim Laden der Profile: {str(e)}')

# Callback to show profile form
@callback(
    [Output('profile-form-container', 'style'),
     Output('editing-profile-id', 'data'),
     Output('editing-profile-index', 'data'),
     Output('profile-name-input', 'value'),
     Output('notification-type-radio', 'value'),
     Output('notification-method-radio', 'value'),
     Output('apprise-urls-textarea', 'value'),
     Output('apprise-section', 'style'),
     Output('email-section', 'style')],
    [Input('add-profile-button', 'n_clicks'),
     Input({'type': 'edit-profile', 'profile_id': dash.ALL}, 'n_clicks')],
    [State('auth-status', 'data')]
)
def show_profile_form(add_clicks, edit_clicks, auth_data):
    if not auth_data or not auth_data.get('authenticated', False):
        return [{'display': 'none'}, None, None, '', 'whitelist', 'apprise', '', {'display': 'block'}, {'display': 'none'}]

    # Check if add button was clicked
    ctx = callback_context
    if not ctx.triggered:
        return [{'display': 'none'}, None, None, '', 'whitelist', 'apprise', '', {'display': 'block'}, {'display': 'none'}]

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'add-profile-button':
        # Show empty form for new profile
        return [{'display': 'block'}, None, None, '', 'whitelist', 'apprise', '', {'display': 'block'}, {'display': 'none'}]
    else:
        # Show form with existing profile data for editing
        try:
            # Parse the button_id which is a string representation of a dict
            import ast
            button_data = ast.literal_eval(button_id)
            profile_id = button_data['profile_id']

            print(f"DEBUG: Editing profile with ID: {profile_id}")

            # Load profile from database
            with get_db_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT name, type, ci_list, apprise_urls, apprise_urls_salt, email_notifications
                    FROM notification_profiles
                    WHERE id = %s
                """, (profile_id,))
                profile = cur.fetchone()

                if profile:
                    name, notification_type, ci_list_db, apprise_urls_db, apprise_urls_salt_db, email_notifications = profile
                    ci_list = ci_list_db if ci_list_db is not None else [] # Ensure ci_list is a list

                    # Decrypt Apprise URLs for editing
                    apprise_urls_text = ''
                    if apprise_urls_db and apprise_urls_salt_db:
                        try:
                            decrypted_urls = []
                            encryption_key = os.getenv('ENCRYPTION_KEY')
                            if encryption_key:
                                encryption_key = encryption_key.encode()
                                for i, encrypted_url in enumerate(apprise_urls_db):
                                    if i < len(apprise_urls_salt_db):
                                        decrypted = decrypt_data(encrypted_url, apprise_urls_salt_db[i], encryption_key)
                                        if decrypted:
                                            decrypted_urls.append(decrypted)
                            apprise_urls_text = '\n'.join(decrypted_urls)
                        except Exception as e:
                            print(f"Error decrypting Apprise URLs: {e}")
                            apprise_urls_text = ''

                    notification_method = 'email' if email_notifications else 'apprise'

                    print(f"DEBUG: Loaded profile - name: {name}, ci_list: {ci_list}, ci_list type: {type(ci_list)}")

                    apprise_section_style = {'display': 'block'} if notification_method == 'apprise' else {'display': 'none'}
                    email_section_style = {'display': 'block'} if notification_method == 'email' else {'display': 'none'}

                    return [
                        {'display': 'block'},
                        profile_id,
                        profile_id,  # Set editing-profile-index to profile_id for consistency
                        name or '',
                        notification_type or 'whitelist',
                        notification_method,
                        apprise_urls_text,
                        apprise_section_style,
                        email_section_style
                    ]
        except Exception:
            pass

    return [{'display': 'none'}, None, None, '', 'whitelist', 'apprise', '', {'display': 'block'}, {'display': 'none'}]

# Note: notification method toggle integrated into show_profile_form callback

# Callback to save profile
@callback(
   [Output('form-error', 'children'),
     Output('save-profile-button', 'n_clicks')],
    [Input('save-profile-button', 'n_clicks'),
     Input('cancel-profile-button', 'n_clicks')],
    [State('editing-profile-id', 'data'),
     State('profile-name-input', 'value'),
     State('notification-type-radio', 'value'),
     State('notification-method-radio', 'value'),
     State('apprise-urls-textarea', 'value'),
     State('selected-cis-data', 'data'),
     State('auth-status', 'data')],
    prevent_initial_call=True
)
def handle_profile_form(save_clicks, cancel_clicks, edit_id, name, notification_type, notification_method, apprise_urls, selected_cis, auth_data):
    # Check which button was clicked
    ctx = callback_context
    if not ctx.triggered:
        return [no_update, 0]

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Handle cancel button
    if button_id == 'cancel-profile-button':
        return ['', 0]

    # Handle save button
    if button_id == 'save-profile-button' and save_clicks > 0:
        # Validate inputs
        if not name or name.strip() == '':
            return ['Profilname ist erforderlich.', 0]

        user_id = auth_data.get('user_id')
        if not user_id:
            return ['Benutzer nicht authentifiziert.', 0]

        # Get selected CIs from the selected-cis-data store
        ci_items = selected_cis if selected_cis else []

        # Process notification method
        email_notifications = notification_method == 'email'
        email_address = auth_data.get('email') if email_notifications else None

        # Process Apprise URLs only if using Apprise method
        url_items = []
        if notification_method == 'apprise':
            url_items = [url.strip() for url in apprise_urls.split('\n') if url.strip()]

            # Validate Apprise URLs
            if url_items and not validate_apprise_urls(url_items):
                return ['Eine oder mehrere Apprise-URLs sind ungültig.', 0]

        try:
            # Save profile to database using encryption functions
            if edit_id:
                # Update existing profile
                success = update_notification_profile(edit_id, user_id, name, notification_type, ci_items, url_items, email_notifications, email_address)
                if not success:
                    return ['Fehler beim Aktualisieren des Profils.', 0]
            else:
                # Add new profile
                profile_id = create_notification_profile(user_id, name, notification_type, ci_items, url_items, email_notifications, email_address)
                if not profile_id:
                    return ['Fehler beim Erstellen des Profils.', 0]

            return ['', 0]  # Success: clear error and reset clicks
        except Exception as e:
            return [f'Fehler beim Speichern: {str(e)}', 0]

    return ['', 0]

# Callback to handle delete confirmation
@callback(
    [     Output('delete-confirm', 'displayed'),
     Output('delete-index-store', 'data')],
    [Input({'type': 'delete-profile', 'profile_id': dash.ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def show_delete_confirm(delete_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return [False, None]

    # Get the triggered input that caused this callback
    triggered_input = ctx.triggered[0]

    # Only show confirmation if a delete button was actually clicked (n_clicks > 0)
    if triggered_input['value'] <= 0:
        return [False, None]

    try:
        button_id = triggered_input['prop_id'].split('.')[0]
        button_data = json.loads(button_id.replace("'", '"'))
        profile_id = button_data['profile_id']

        # Get profile name for confirmation message
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT name FROM notification_profiles WHERE id = %s
            """, (profile_id,))
            result = cur.fetchone()
            profile_name = result[0] if result else 'Unbenanntes Profil'

        message = f'Sind Sie sicher, dass Sie das Profil "{profile_name}" löschen möchten?'
        return [True, profile_id]
    except Exception as e:
        print(f"Error in show_delete_confirm: {e}")

    return [False, None]

# Note: Problematic delete_profile callback removed - delete logic handled by ConfirmDialog

# Callback to test Apprise notification
@callback(
    Output('test-result', 'children'),
    [Input('test-notification-button', 'n_clicks')],
    [State('test-apprise-url', 'value'),
     State('auth-status', 'data')],
    prevent_initial_call=True
)
def test_apprise_notification(n_clicks, apprise_url, auth_data):
    if not auth_data.get('authenticated', False):
        return html.Div('Authentifizierung erforderlich.', style={'color': 'red'})

    if not apprise_url or not apprise_url.strip():
        return html.Div('Bitte geben Sie eine Apprise-URL zum Testen ein.', style={'color': 'orange'})

    try:
        # Create Apprise object and add the URL
        apobj = apprise.Apprise()

        # Add the URL and check if it was added successfully
        if not apobj.add(apprise_url.strip()):
            return html.Div([
                html.I(className='material-icons', children='error', style={'color': 'red', 'margin-right': '8px'}),
                html.Span('Ungültiges Apprise-URL-Format. Bitte überprüfen Sie die URL-Syntax.', style={'color': 'red'}),
                html.Br(),
                html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
                html.Br(),
                html.Br(),
                html.Span('Für korrekte URL-Formate besuchen Sie:', style={'color': 'blue', 'font-weight': 'bold'}),
                html.Br(),
                html.A('https://github.com/caronc/apprise/wiki', href='https://github.com/caronc/apprise/wiki', target='_blank', style={'color': 'blue', 'text-decoration': 'underline'})
            ])

        # Send test notification
        result = apobj.notify(
            title='TI-Monitoring Test-Benachrichtigung',
            body='Dies ist eine Test-Benachrichtigung von TI-Monitoring. Wenn Sie diese erhalten, funktioniert Ihre Apprise-Konfiguration korrekt!',
            body_format=apprise.NotifyFormat.TEXT
        )

        if result:
            return html.Div([
                html.I(className='material-icons', children='check_circle', style={'color': 'green', 'margin-right': '8px'}),
                html.Span('Test-Benachrichtigung erfolgreich gesendet! Überprüfen Sie Ihr Benachrichtigungsziel.', style={'color': 'green'}),
                html.Br(),
                html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
                html.Br(),
                html.Span('Hinweis: Wenn Sie die Nachricht nicht erhalten, überprüfen Sie Ihr Benachrichtigungsziel und die entsprechenden Berechtigungen.', style={'color': 'blue', 'font-size': '0.9em'})
            ])
        else:
            return html.Div([
                html.I(className='material-icons', children='error', style={'color': 'red', 'margin-right': '8px'}),
                html.Span('Test-Benachrichtigung konnte nicht gesendet werden. Bitte überprüfen Sie Ihre Apprise-URL und Konfiguration.', style={'color': 'red'}),
                html.Br(),
                html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
                html.Br(),
                html.Br(),
                html.Span('Für weitere Hilfe und Troubleshooting besuchen Sie:', style={'color': 'blue', 'font-weight': 'bold'}),
                html.Br(),
                html.A('https://github.com/caronc/apprise/wiki', href='https://github.com/caronc/apprise/wiki', target='_blank', style={'color': 'blue', 'text-decoration': 'underline'}),
                html.Br(),
                html.Br(),
                html.Span('Häufige Probleme:', style={'color': 'orange', 'font-weight': 'bold'}),
                html.Br(),
                html.Span('• Überprüfen Sie, ob der Server erreichbar ist', style={'color': 'orange'}),
                html.Br(),
                html.Span('• Überprüfen Sie Benutzername/Passwort-Anmeldedaten', style={'color': 'orange'}),
                html.Br(),
                html.Span('• Stellen Sie sicher, dass die Berechtigungen korrekt sind', style={'color': 'orange'}),
                html.Br(),
                html.Span('• Überprüfen Sie die Server-Logs auf Fehler', style={'color': 'orange'})
            ])

    except Exception as e:
        return html.Div([
            html.I(className='material-icons', children='error', style={'color': 'red', 'margin-right': '8px'}),
            html.Span(f'Fehler beim Testen der Benachrichtigung: {str(e)}', style={'color': 'red'}),
            html.Br(),
            html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
            html.Br(),
            html.Br(),
                html.Span('Für weitere Hilfe und URL-Beispiele besuchen Sie:', style={'color': 'blue', 'font-weight': 'bold'}),
                html.Br(),
                html.A('https://github.com/caronc/apprise/wiki', href='https://github.com/caronc/apprise/wiki', target='_blank', style={'color': 'blue', 'text-decoration': 'underline'})
        ])
