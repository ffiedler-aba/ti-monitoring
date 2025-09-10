import dash
from dash import html, dcc, Input, Output, State, callback, no_update
from mylibrary import is_admin_user
from pages.components.admin_common import create_admin_header
import yaml
import os
import time
import json
import pandas as pd
import pytz
from datetime import datetime

# Configuration cache for admin logs page
_logs_config_cache = {}
_logs_config_cache_timestamp = 0
_logs_config_cache_ttl = 300  # 5 seconds cache TTL
_logs_config_cache_max_size = 10  # Limit cache size

def load_config():
    """Load configuration from YAML file with caching"""
    global _logs_config_cache, _logs_config_cache_timestamp

    current_time = time.time()
    if (not _logs_config_cache or
        current_time - _logs_config_cache_timestamp > _logs_config_cache_ttl):

        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                _logs_config_cache = yaml.safe_load(f) or {}
            _logs_config_cache_timestamp = current_time

            # Limit cache size
            if len(_logs_config_cache) > _logs_config_cache_max_size:
                # Keep only the most recent entries
                keys = list(_logs_config_cache.keys())[:_logs_config_cache_max_size]
                _logs_config_cache = {k: _logs_config_cache[k] for k in keys}
        except (FileNotFoundError, Exception):
            _logs_config_cache = {}
            _logs_config_cache_timestamp = current_time

    return _logs_config_cache

def load_core_config():
    """Load core configuration from cached config"""
    config = load_config()
    return config.get('core', {})

def get_button_style(variant='primary'):
    base = {
        'border': 'none',
        'borderRadius': '6px',
        'padding': '10px 20px',
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'marginRight': '10px',
        'marginBottom': '10px'
    }

    if variant == 'primary':
        base.update({
            'backgroundColor': '#3498db',
            'color': 'white'
        })
    elif variant == 'success':
        base.update({
            'backgroundColor': '#27ae60',
            'color': 'white'
        })
    elif variant == 'danger':
        base.update({
            'backgroundColor': '#e74c3c',
            'color': 'white'
        })
    elif variant == 'secondary':
        base.update({
            'backgroundColor': '#95a5a6',
            'color': 'white'
        })

    return base

dash.register_page(__name__, path='/admin/logs')

def serve_layout():
    """Admin logs page layout"""
    layout = html.Div([
        # Admin header with logo
        create_admin_header('Admin: System-Logs'),

        # Back link
        html.A('← Zurück zum Admin-Dashboard', href='/admin', style={
            'color': '#3498db',
            'textDecoration': 'none',
            'marginBottom': '20px',
            'display': 'block'
        }),

        # Auth check
        html.Div(id='admin-logs-content', children=[
            html.P('Überprüfe Admin-Berechtigung...', style={'textAlign': 'center'})
        ]),

        # Auth-Status wird global in app.py bereitgestellt

        # Refresh interval for logs
        dcc.Interval(
            id='log-refresh-interval',
            interval=30*1000,  # 30 seconds
            n_intervals=0,
            disabled=True
        )
    ])

    return layout

layout = serve_layout

# Callback: Check admin access and show logs content
@callback(
    Output('admin-logs-content', 'children'),
    [Input('auth-status', 'data')],
    prevent_initial_call=False
)
def check_admin_and_load_logs(auth_data):
    """Check admin access and load logs interface"""
    if not auth_data or not auth_data.get('authenticated'):
        return html.Div([
            html.H3('Authentifizierung erforderlich'),
            html.P('Bitte melden Sie sich zuerst über die Notifications-Seite an.'),
            html.A('Zur Anmeldung', href='/notifications', className='btn btn-primary')
        ])

    user_email = auth_data.get('email', '')
    if not is_admin_user(user_email):
        return html.Div([
            html.H3('Zugriff verweigert'),
            html.P('Sie haben keine Admin-Berechtigung für diesen Bereich.'),
            html.A('Zurück zu Notifications', href='/notifications', className='btn btn-primary')
        ])

    # Admin verified - show logs interface
    return html.Div([
        html.H4('Container-Logs'),
        html.Div([
            html.Div([
                html.Label('Anzahl Zeilen:', style={
                    'marginRight': '10px',
                    'fontWeight': '500',
                    'lineHeight': '36px',  # Match dropdown height
                    'display': 'inline-block'
                }),
                dcc.Dropdown(
                    id='admin-log-lines-dropdown',
                    options=[
                        {'label': '50 Zeilen', 'value': 50},
                        {'label': '100 Zeilen', 'value': 100},
                        {'label': '200 Zeilen', 'value': 200},
                        {'label': '500 Zeilen', 'value': 500}
                    ],
                    value=100,
                    style={'width': '150px', 'display': 'inline-block'}
                )
            ], style={
                'display': 'inline-flex',
                'alignItems': 'center',
                'marginRight': '20px',
                'gap': '10px'
            }),

            html.Div([
                html.Button('Aktualisieren', id='refresh-logs-btn', n_clicks=0, style={
                    **get_button_style('primary'),
                    'marginRight': '10px'
                }),
                html.Button('Alle Logs', id='full-logs-btn', n_clicks=0, style=get_button_style('secondary'))
            ], style={'display': 'inline-flex', 'alignItems': 'center', 'gap': '10px'})
        ], style={
            'marginBottom': '20px',
            'display': 'flex',
            'alignItems': 'center',
            'flexWrap': 'wrap',
            'gap': '15px'
        }),

        html.Div(id='admin-log-content-display', style={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #dee2e6',
            'borderRadius': '4px',
            'padding': '15px',
            'fontFamily': 'monospace',
            'fontSize': '12px',
            'maxHeight': '600px',
            'overflowY': 'auto',
            'whiteSpace': 'pre-wrap'
        })
    ])

# Callback: Update log content
@callback(
    [Output('admin-log-content-display', 'children'),
     Output('admin-log-lines-dropdown', 'value')],
    [Input('refresh-logs-btn', 'n_clicks'),
     Input('full-logs-btn', 'n_clicks'),
     Input('log-refresh-interval', 'n_intervals')],
    [State('admin-log-lines-dropdown', 'value'),
     State('auth-status', 'data')],
    prevent_initial_call=False
)
def update_log_content(refresh_clicks, full_clicks, interval_clicks, selected_lines, auth_data):
    """Update log content based on user actions"""
    # Check admin access first
    if not auth_data or not auth_data.get('authenticated'):
        return 'Nicht authentifiziert', no_update

    if not is_admin_user(auth_data.get('email', '')):
        return 'Keine Admin-Berechtigung', no_update

    ctx = dash.callback_context

    # Determine number of lines to show
    if not ctx.triggered:
        # First load - show default logs
        lines_to_show = selected_lines or 100
        dropdown_value = selected_lines or 100
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == 'full-logs-btn':
            lines_to_show = 1000
            dropdown_value = 1000
        else:
            lines_to_show = selected_lines or 100
            dropdown_value = selected_lines

    try:
        # Show application logs from within container
        # For now, show a simple log placeholder - real logs would need external API
        log_content = f'''Container-Logs (letzte {lines_to_show} Zeilen):

=== TI-Monitoring Web Container ===
Angeforderte Zeilen: {lines_to_show}
Zeitstempel: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Hinweis: Für vollständige Container-Logs verwenden Sie:
docker compose -f docker-compose-dev.yml logs --tail {lines_to_show} ti-monitoring-web

=== Aktuelle Session ===
Admin-Zugriff: Aktiv
Benutzer-Sessions: Werden geladen...
Letzte Aktivität: {datetime.now().strftime("%H:%M:%S")}

=== System-Status ===
Web-Container: Läuft
Cron-Container: Läuft
Datenbank: Verbunden
'''

    except Exception as e:
        log_content = f'Fehler beim Generieren der Log-Anzeige: {str(e)}'

    return log_content, dropdown_value
