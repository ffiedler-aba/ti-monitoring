import dash
from dash import html, dcc, Input, Output, State, callback
from mylibrary import *
import yaml
import os
import time
import json
import pandas as pd
import pytz
from datetime import datetime

# Configuration cache for logs page
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

def get_log_file_path():
    """Get the path to the cron log file"""
    return os.path.join(os.path.dirname(__file__), '..', 'data', 'cron.log')

def get_log_file_info():
    """Get information about the log file"""
    log_file_path = get_log_file_path()

    if not os.path.exists(log_file_path):
        return {
            'exists': False,
            'size': 0,
            'modified': None,
            'lines': 0
        }

    try:
        stat = os.stat(log_file_path)
        size = stat.st_size

        # Count lines
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = sum(1 for _ in f)

        # Get modification time in Europe/Berlin timezone
        modified_timestamp = datetime.fromtimestamp(stat.st_mtime, tz=pytz.timezone('Europe/Berlin'))

        return {
            'exists': True,
            'size': size,
            'modified': modified_timestamp,
            'lines': lines
        }
    except Exception as e:
        return {
            'exists': False,
            'size': 0,
            'modified': None,
            'lines': 0,
            'error': str(e)
        }

def read_log_tail(lines=100):
    """Read the last N lines from the log file and reverse them (newest first)"""
    log_file_path = get_log_file_path()

    if not os.path.exists(log_file_path):
        return "Log-Datei nicht gefunden: data/cron.log"

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()

        # Get last N lines
        tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Reverse the order so newest lines appear first
        tail_lines.reverse()

        return ''.join(tail_lines)
    except Exception as e:
        return f"Fehler beim Lesen der Log-Datei: {e}"

def get_app_status():
    """Return status dict for the web app itself (this page is served → running)."""
    return { 'label': 'App', 'status': 'OK', 'detail': 'Web-App läuft', 'color': 'green' }

def get_cron_status():
    """Determine cron status from log freshness."""
    info = get_log_file_info()
    if not info['exists']:
        return { 'label': 'Cron', 'status': 'Fehlt', 'detail': 'Keine Log-Datei gefunden', 'color': 'red' }
    try:
        now = datetime.now(pytz.timezone('Europe/Berlin'))
        age_sec = (now - info['modified']).total_seconds() if info['modified'] else 1e9
        if age_sec < 600:  # < 10 Minuten
            return { 'label': 'Cron', 'status': 'OK', 'detail': 'Letzte Aktivität < 10 min', 'color': 'green' }
        elif age_sec < 3600:
            return { 'label': 'Cron', 'status': 'Alt', 'detail': 'Letzte Aktivität < 60 min', 'color': 'orange' }
        else:
            return { 'label': 'Cron', 'status': 'Stale', 'detail': 'Letzte Aktivität > 60 min', 'color': 'red' }
    except Exception as e:
        return { 'label': 'Cron', 'status': 'Fehler', 'detail': str(e), 'color': 'red' }

def get_db_status():
    """Ping DB using get_db_conn()."""
    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute('SELECT 1')
            _ = cur.fetchone()
        return { 'label': 'Datenbank', 'status': 'OK', 'detail': 'Verbindung erfolgreich', 'color': 'green' }
    except Exception as e:
        return { 'label': 'Datenbank', 'status': 'Fehler', 'detail': str(e), 'color': 'red' }

def render_status_badge(item):
    return html.Div(
        style={
            'border': f"1px solid {'#2ecc71' if item['color']=='green' else ('#f39c12' if item['color']=='orange' else '#e74c3c')}",
            'borderRadius': '8px',
            'padding': '8px 12px',
            'minWidth': '220px'
        },
        children=[
            html.Div([
                html.Strong(item['label']),
                html.Span(f" – {item['status']}", style={'color': item['color'], 'marginLeft': '6px'})
            ]),
            html.Div(item['detail'], style={'fontSize': '0.85em', 'color': '#7f8c8d'})
        ]
    )

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"

dash.register_page(__name__, path='/logs')

def create_log_info_display(log_info):
    """Create the log file information display"""
    if not log_info['exists']:
        return html.Div([
            html.H4('📄 Log-Datei Status'),
            html.Div(className='log-info', children=[
                html.Div(className='log-info-item', children=[
                    html.Strong('Status: '),
                    html.Span('❌ Nicht gefunden', style={'color': 'red'})
                ]),
                html.Div(className='log-info-item', children=[
                    html.Strong('Pfad: '),
                    html.Span('data/cron.log')
                ])
            ])
        ])

    return html.Div([
        html.H4('📄 Log-Datei Status'),
        html.Div(className='log-info', children=[
            html.Div(className='log-info-item', children=[
                html.Strong('Status: '),
                html.Span('✅ Verfügbar', style={'color': 'green'})
            ]),
            html.Div(className='log-info-item', children=[
                html.Strong('Pfad: '),
                html.Span('data/cron.log')
            ]),
            html.Div(className='log-info-item', children=[
                html.Strong('Größe: '),
                html.Span(format_file_size(log_info['size']))
            ]),
            html.Div(className='log-info-item', children=[
                html.Strong('Zeilen: '),
                html.Span(f"{log_info['lines']:,}")
            ]),
            html.Div(className='log-info-item', children=[
                html.Strong('Letzte Änderung: '),
                html.Span(log_info['modified'].strftime('%d.%m.%Y %H:%M:%S %Z') if log_info['modified'] else 'Unbekannt')
            ])
        ])
    ])

def serve_layout():
    # Load core configurations
    core_config = load_core_config()

    # Get log file information
    log_info = get_log_file_info()

    # Get initial log content
    log_content = read_log_tail(100)

    layout = html.Div([
        html.P('Hier können Sie die Log-Datei des Cron-Jobs einsehen. Die Logs werden automatisch täglich rotiert und 7 Tage lang aufbewahrt.'),

        # Status-Kacheln
        html.Div([
            html.H4('🩺 Systemstatus'),
            html.Div(
                style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'},
                children=[
                    render_status_badge(get_app_status()),
                    render_status_badge(get_cron_status()),
                    render_status_badge(get_db_status()),
                ]
            )
        ], style={'marginBottom': '16px'}),

        # Log file information
        create_log_info_display(log_info),

        # Controls
        html.Div(className='log-controls', children=[
            html.H4('🔧 Steuerung'),
            html.Div(className='control-group', children=[
                html.Label('Anzahl Zeilen:'),
                dcc.Dropdown(
                    id='log-lines-dropdown',
                    options=[
                        {'label': '50 Zeilen', 'value': 50},
                        {'label': '100 Zeilen', 'value': 100},
                        {'label': '200 Zeilen', 'value': 200},
                        {'label': '500 Zeilen', 'value': 500},
                        {'label': 'Alle Zeilen', 'value': 0}
                    ],
                    value=100,
                    style={'width': '200px'}
                )
            ]),
            html.Div(className='control-group', children=[
                html.Button('🔄 Aktualisieren', id='refresh-logs-btn', n_clicks=0, className='btn btn-primary'),
                html.Button('📄 Vollständige Logs', id='full-logs-btn', n_clicks=0, className='btn btn-secondary')
            ])
        ]),

        # Log content
        html.Div(className='log-content', children=[
            html.H4('📋 Log-Inhalt'),
            html.Div(
                id='log-content-display',
                children=[
                    html.Pre(
                        log_content,
                        className='log-text',
                        style={
                            'white-space': 'pre-wrap',
                            'font-family': 'monospace',
                            'font-size': '12px',
                            'border-radius': '4px',
                            'padding': '10px',
                            'max-height': '600px',
                            'overflow-y': 'auto'
                        }
                    )
                ]
            )
        ]),

        # Auto-refresh interval
        dcc.Interval(
            id='log-refresh-interval',
            interval=30000,  # 30 seconds
            n_intervals=0
        )
    ])

    return layout

@callback(
    [Output('log-content-display', 'children'),
     Output('log-lines-dropdown', 'value')],
    [Input('refresh-logs-btn', 'n_clicks'),
     Input('full-logs-btn', 'n_clicks'),
     Input('log-refresh-interval', 'n_intervals')],
    [State('log-lines-dropdown', 'value')]
)
def update_log_content(refresh_clicks, full_clicks, interval_clicks, selected_lines):
    """Update log content based on user actions"""
    ctx = dash.callback_context

    if not ctx.triggered:
        return dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Determine number of lines to show
    if trigger_id == 'full-logs-btn':
        lines = 0  # Show all lines
    elif trigger_id == 'log-lines-dropdown':
        lines = selected_lines or 100
    else:
        lines = selected_lines or 100

    # Read log content
    log_content = read_log_tail(lines)

    # Create display
    display = html.Pre(
        log_content,
        className='log-text',
        style={
            'white-space': 'pre-wrap',
            'font-family': 'monospace',
            'font-size': '12px',
            'border-radius': '4px',
            'padding': '10px',
            'max-height': '600px',
            'overflow-y': 'auto'
        }
    )

    return display, lines

layout = serve_layout
