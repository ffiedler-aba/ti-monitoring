import dash
from dash import html, dcc, Input, Output, State, callback, no_update
from mylibrary import is_admin_user, get_db_conn
from pages.components.admin_common import create_admin_header
import pandas as pd
from datetime import datetime, timedelta

dash.register_page(__name__, path='/admin/stats')

def serve_layout():
    """Admin extended statistics page layout"""
    layout = html.Div([
        # Admin header with logo
        create_admin_header('Admin: Erweiterte Statistiken'),

        # Back link
        html.A('← Zurück zum Admin-Dashboard', href='/admin', style={
            'color': '#3498db',
            'textDecoration': 'none',
            'marginBottom': '20px',
            'display': 'block'
        }),

        # Auth check and main content
        html.Div(id='admin-stats-content', children=[
            html.P('Überprüfe Admin-Berechtigung...', style={'textAlign': 'center'})
        ]),

        # Auth-Status wird global in app.py bereitgestellt
    ])

    return layout

layout = serve_layout

# Callback: Check admin access and show stats interface
@callback(
    Output('admin-stats-content', 'children'),
    [Input('auth-status', 'data')],
    prevent_initial_call=False
)
def check_admin_and_load_stats(auth_data):
    """Check admin access and load stats interface"""
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

    # Admin verified - show stats interface
    return html.Div([
        html.H4('Erweiterte Notification-Statistiken'),

        # Time period selector
        html.Div([
            html.Label('Zeitraum:', style={'marginRight': '10px', 'fontWeight': '500'}),
            dcc.Dropdown(
                id='stats-timeframe-dropdown',
                options=[
                    {'label': 'Letzte 24 Stunden', 'value': 24},
                    {'label': 'Letzte 7 Tage', 'value': 168},
                    {'label': 'Letzte 30 Tage', 'value': 720},
                    {'label': 'Alle Zeit', 'value': 0}
                ],
                value=24,
                style={'width': '200px', 'display': 'inline-block'}
            ),
            html.Button('Aktualisieren', id='refresh-stats-btn', n_clicks=0,
                       style={'marginLeft': '15px', 'padding': '8px 16px'})
        ], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'}),

        # Statistics content
        html.Div(id='notification-stats-display')
    ])

# Callback: Load notification statistics
@callback(
    Output('notification-stats-display', 'children'),
    [Input('refresh-stats-btn', 'n_clicks'),
     Input('stats-timeframe-dropdown', 'value')],
    [State('auth-status', 'data')],
    prevent_initial_call=False
)
def load_notification_stats(refresh_clicks, timeframe_hours, auth_data):
    """Load notification statistics from database"""
    if not auth_data or not auth_data.get('authenticated'):
        return html.P('Nicht authentifiziert')

    if not is_admin_user(auth_data.get('email', '')):
        return html.P('Keine Admin-Berechtigung')

    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            # Build time filter
            time_filter = ""
            if timeframe_hours > 0:
                time_filter = f"WHERE sent_at > NOW() - INTERVAL '{timeframe_hours} hours'"

            # Get notification counts
            cur.execute(f"""
                SELECT
                    COUNT(*) as total_notifications,
                    COUNT(*) FILTER (WHERE delivery_status = 'sent') as sent_count,
                    COUNT(*) FILTER (WHERE delivery_status = 'failed') as failed_count,
                    COUNT(*) FILTER (WHERE notification_type = 'incident') as incident_count,
                    COUNT(*) FILTER (WHERE notification_type = 'recovery') as recovery_count,
                    COUNT(*) FILTER (WHERE recipient_type = 'email') as email_count,
                    COUNT(*) FILTER (WHERE recipient_type = 'apprise') as apprise_count
                FROM notification_logs
                {time_filter}
            """)
            stats = cur.fetchone()

            if not stats or stats[0] == 0:
                return html.Div([
                    html.H5('Keine Notification-Logs gefunden'),
                    html.P(f'Zeitraum: {timeframe_hours} Stunden' if timeframe_hours > 0 else 'Alle Zeit'),
                    html.P('Hinweis: Logs werden erst nach der ersten Benachrichtigung mit der neuen Version erstellt.')
                ])

            total, sent, failed, incidents, recoveries, email, apprise = stats
            success_rate = (sent / total * 100) if total > 0 else 0

            # Create statistics display
            stats_display = html.Div([
                html.H5(f'Notification-Statistiken ({timeframe_hours}h)' if timeframe_hours > 0 else 'Notification-Statistiken (Alle Zeit)'),

                # Overview cards
                html.Div([
                    html.Div([
                        html.H6(f'{total}', style={'margin': '0', 'fontSize': '20px', 'color': '#3498db'}),
                        html.P('Gesamt', style={'margin': '0', 'color': '#7f8c8d'})
                    ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '100px'}),

                    html.Div([
                        html.H6(f'{sent}', style={'margin': '0', 'fontSize': '20px', 'color': '#27ae60'}),
                        html.P('Erfolgreich', style={'margin': '0', 'color': '#7f8c8d'})
                    ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '100px'}),

                    html.Div([
                        html.H6(f'{failed}', style={'margin': '0', 'fontSize': '20px', 'color': '#e74c3c'}),
                        html.P('Fehlgeschlagen', style={'margin': '0', 'color': '#7f8c8d'})
                    ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '100px'}),

                    html.Div([
                        html.H6(f'{success_rate:.1f}%', style={'margin': '0', 'fontSize': '20px', 'color': '#f39c12'}),
                        html.P('Erfolgsrate', style={'margin': '0', 'color': '#7f8c8d'})
                    ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '100px'})
                ], style={'display': 'flex', 'gap': '15px', 'flexWrap': 'wrap', 'marginBottom': '20px'}),

                # Type breakdown
                html.H6('Nach Typ:'),
                html.Div([
                    html.P(f'🚨 Incidents: {incidents}'),
                    html.P(f'✅ Recoveries: {recoveries}'),
                    html.P(f'📧 E-Mail: {email}'),
                    html.P(f'📱 Apprise: {apprise}')
                ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '10px', 'marginBottom': '20px'}),

                # Recent logs table
                html.H6('Letzte Benachrichtigungen:'),
                html.Div(id='recent-notifications-table'),

                # Apprise prefix analysis
                html.Hr(),
                html.H6('Apprise-Provider-Analyse:'),
                html.Div(id='apprise-prefix-analysis')
            ])

            return stats_display

    except Exception as e:
        return html.P(f'Fehler beim Laden der Statistiken: {str(e)}', style={'color': '#e74c3c'})

# Callback: Load recent notifications table
@callback(
    Output('recent-notifications-table', 'children'),
    [Input('refresh-stats-btn', 'n_clicks'),
     Input('stats-timeframe-dropdown', 'value')],
    [State('auth-status', 'data')],
    prevent_initial_call=False
)
def load_recent_notifications(refresh_clicks, timeframe_hours, auth_data):
    """Load recent notification logs table"""
    if not auth_data or not auth_data.get('authenticated'):
        return html.Div()

    if not is_admin_user(auth_data.get('email', '')):
        return html.Div()

    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            time_filter = ""
            if timeframe_hours > 0:
                time_filter = f"WHERE nl.sent_at > NOW() - INTERVAL '{timeframe_hours} hours'"

            cur.execute(f"""
                SELECT nl.ci, nl.notification_type, nl.delivery_status,
                       nl.recipient_type, nl.sent_at, np.name as profile_name,
                       nl.error_message
                FROM notification_logs nl
                JOIN notification_profiles np ON nl.profile_id = np.id
                {time_filter}
                ORDER BY nl.sent_at DESC
                LIMIT 20
            """)
            logs = cur.fetchall()

            if not logs:
                return html.P('Keine aktuellen Benachrichtigungen gefunden.')

            # Create table
            table = html.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Zeit'),
                        html.Th('CI'),
                        html.Th('Typ'),
                        html.Th('Status'),
                        html.Th('Kanal'),
                        html.Th('Profil'),
                        html.Th('Fehler')
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(str(log[4])[:16]),  # sent_at
                        html.Td(str(log[0])),       # ci
                        html.Td('🚨' if log[1] == 'incident' else '✅'),  # notification_type
                        html.Td('✅' if log[2] == 'sent' else '❌'),       # delivery_status
                        html.Td('📧' if log[3] == 'email' else '📱'),     # recipient_type
                        html.Td(str(log[5])),       # profile_name
                        html.Td(str(log[6])[:30] + '...' if log[6] else '-')  # error_message
                    ]) for log in logs
                ])
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'border': '1px solid #ddd',
                'fontSize': '12px'
            })

            return table

    except Exception as e:
        return html.P(f'Fehler beim Laden der Logs: {str(e)}', style={'color': '#e74c3c'})

# Callback: Load Apprise prefix analysis
@callback(
    Output('apprise-prefix-analysis', 'children'),
    [Input('refresh-stats-btn', 'n_clicks')],
    [State('auth-status', 'data')],
    prevent_initial_call=False
)
def load_apprise_analysis(refresh_clicks, auth_data):
    """Analyze Apprise URL prefixes from user profiles"""
    if not auth_data or not auth_data.get('authenticated'):
        return html.Div()

    if not is_admin_user(auth_data.get('email', '')):
        return html.Div()

    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            # Get all apprise URLs from profiles (encrypted)
            cur.execute("""
                SELECT np.apprise_urls, np.apprise_urls_salt
                FROM notification_profiles np
                WHERE np.apprise_urls IS NOT NULL
                  AND array_length(np.apprise_urls, 1) > 0
            """)
            profiles = cur.fetchall()

            if not profiles:
                return html.P('Keine Apprise-Profile gefunden.')

            # Decrypt and analyze prefixes
            from mylibrary import decrypt_data
            import os

            prefix_counts = {}
            total_urls = 0

            encryption_key = os.getenv('ENCRYPTION_KEY')
            if encryption_key:
                encryption_key = encryption_key.encode()

            for apprise_urls, salts in profiles:
                if apprise_urls and salts:
                    for i, encrypted_url in enumerate(apprise_urls):
                        if i < len(salts):
                            try:
                                decrypted = decrypt_data(encrypted_url, salts[i], encryption_key)
                                if decrypted:
                                    # Extract prefix (e.g., "resend://", "tgram://", "mailto://")
                                    prefix = decrypted.split('://')[0] + '://' if '://' in decrypted else 'unknown'
                                    prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
                                    total_urls += 1
                            except Exception:
                                prefix_counts['decrypt_error'] = prefix_counts.get('decrypt_error', 0) + 1

            if not prefix_counts:
                return html.P('Keine auswertbaren Apprise-URLs gefunden.')

            # Create analysis display
            analysis = html.Div([
                html.P(f'Analysierte URLs: {total_urls}'),
                html.Div([
                    html.Div([
                        html.Strong(prefix),
                        html.Span(f': {count} ({count/total_urls*100:.1f}%)' if total_urls > 0 else f': {count}')
                    ], style={'marginBottom': '5px'}) for prefix, count in sorted(prefix_counts.items(), key=lambda x: x[1], reverse=True)
                ])
            ])

            return analysis

    except Exception as e:
        return html.P(f'Fehler bei der Apprise-Analyse: {str(e)}', style={'color': '#e74c3c'})
