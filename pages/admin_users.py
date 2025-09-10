import dash
from dash import html, dcc, Input, Output, State, callback, no_update
from mylibrary import is_admin_user, get_user_by_email, get_db_conn
from pages.components.admin_common import create_admin_header
import pandas as pd
from datetime import datetime, timedelta

dash.register_page(__name__, path='/admin/users')

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
        base.update({'backgroundColor': '#3498db', 'color': 'white'})
    elif variant == 'success':
        base.update({'backgroundColor': '#27ae60', 'color': 'white'})
    elif variant == 'danger':
        base.update({'backgroundColor': '#e74c3c', 'color': 'white'})
    elif variant == 'secondary':
        base.update({'backgroundColor': '#95a5a6', 'color': 'white'})

    return base

def serve_layout():
    """Admin users page layout"""
    layout = html.Div([
        # Admin header with logo
        create_admin_header('Admin: Benutzerverwaltung'),

        # Back link
        html.A('← Zurück zum Admin-Dashboard', href='/admin', style={
            'color': '#3498db',
            'textDecoration': 'none',
            'marginBottom': '20px',
            'display': 'block'
        }),

        # Auth check and main content
        html.Div(id='admin-users-content', children=[
            html.P('Überprüfe Admin-Berechtigung...', style={'textAlign': 'center'})
        ]),

        # Auth-Status wird global in app.py bereitgestellt
    ])

    return layout

layout = serve_layout

# Callback: Check admin access and show users interface
@callback(
    Output('admin-users-content', 'children'),
    [Input('auth-status', 'data')],
    prevent_initial_call=False
)
def check_admin_and_load_users(auth_data):
    """Check admin access and load users interface"""
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

    # Admin verified - show users interface
    return html.Div([
        # Statistics section
        html.Div(id='user-statistics', style={'marginBottom': '30px'}),

        # User search section
        html.Div([
            html.H4('Benutzer-Suche'),
            html.Div([
                html.Div([
                    html.Label('E-Mail-Adresse:', style={
                        'marginRight': '10px',
                        'fontWeight': '500',
                        'lineHeight': '36px'
                    }),
                    dcc.Input(
                        id='user-search-input',
                        type='email',
                        placeholder='user@example.com',
                        style={
                            'width': '250px',
                            'padding': '8px 12px',
                            'border': '1px solid #ddd',
                            'borderRadius': '4px',
                            'marginRight': '10px'
                        }
                    )
                ], style={'display': 'inline-flex', 'alignItems': 'center', 'marginRight': '15px'}),

                html.Button('Suchen', id='search-user-btn', n_clicks=0, style=get_button_style('primary'))
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),

            # Search results
            html.Div(id='user-search-results')
        ], style={'marginBottom': '30px'}),

        # All users section
        html.Div([
            html.H4('Alle Benutzer'),
            html.Button('Liste aktualisieren', id='refresh-users-btn', n_clicks=0, style=get_button_style('secondary')),
            html.Div(id='all-users-list', style={'marginTop': '15px'})
        ])
    ])

# Callback: Load and display user statistics
@callback(
    Output('user-statistics', 'children'),
    [Input('auth-status', 'data'),
     Input('refresh-users-btn', 'n_clicks')],
    prevent_initial_call=False
)
def load_user_statistics(auth_data, refresh_clicks):
    """Load user statistics for admin dashboard"""
    if not auth_data or not auth_data.get('authenticated'):
        return html.Div()

    if not is_admin_user(auth_data.get('email', '')):
        return html.Div()

    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            # Get user counts
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM notification_profiles")
            total_profiles = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM notification_profiles WHERE email_notifications = TRUE")
            email_profiles = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM notification_profiles WHERE apprise_urls IS NOT NULL AND array_length(apprise_urls, 1) > 0")
            apprise_profiles = cur.fetchone()[0]

            # Get recent activity (last 24h)
            cur.execute("""
                SELECT COUNT(*) FROM users
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            new_users_24h = cur.fetchone()[0]

        # Create statistics display
        stats = html.Div([
            html.H4('System-Statistiken'),
            html.Div([
                html.Div([
                    html.H5(f'{total_users}', style={'margin': '0', 'fontSize': '24px', 'color': '#3498db'}),
                    html.P('Benutzer gesamt', style={'margin': '0', 'color': '#7f8c8d'})
                ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '120px'}),

                html.Div([
                    html.H5(f'{total_profiles}', style={'margin': '0', 'fontSize': '24px', 'color': '#27ae60'}),
                    html.P('Profile gesamt', style={'margin': '0', 'color': '#7f8c8d'})
                ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '120px'}),

                html.Div([
                    html.H5(f'{email_profiles}', style={'margin': '0', 'fontSize': '24px', 'color': '#f39c12'}),
                    html.P('E-Mail Profile', style={'margin': '0', 'color': '#7f8c8d'})
                ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '120px'}),

                html.Div([
                    html.H5(f'{apprise_profiles}', style={'margin': '0', 'fontSize': '24px', 'color': '#9b59b6'}),
                    html.P('Apprise Profile', style={'margin': '0', 'color': '#7f8c8d'})
                ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '120px'}),

                html.Div([
                    html.H5(f'{new_users_24h}', style={'margin': '0', 'fontSize': '24px', 'color': '#e74c3c'}),
                    html.P('Neue (24h)', style={'margin': '0', 'color': '#7f8c8d'})
                ], style={'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'minWidth': '120px'})
            ], style={'display': 'flex', 'gap': '15px', 'flexWrap': 'wrap'})
        ], style={'marginBottom': '30px'})

        return stats

    except Exception as e:
        return html.Div([
            html.H4('Statistiken'),
            html.P(f'Fehler beim Laden der Statistiken: {str(e)}', style={'color': '#e74c3c'})
        ])

# Callback: Search for specific user
@callback(
    Output('user-search-results', 'children'),
    [Input('search-user-btn', 'n_clicks')],
    [State('user-search-input', 'value'),
     State('auth-status', 'data')],
    prevent_initial_call=True
)
def search_user(search_clicks, email, auth_data):
    """Search for user by email address"""
    if not search_clicks or not email:
        return html.Div()

    if not auth_data or not auth_data.get('authenticated'):
        return html.P('Nicht authentifiziert', style={'color': '#e74c3c'})

    if not is_admin_user(auth_data.get('email', '')):
        return html.P('Keine Admin-Berechtigung', style={'color': '#e74c3c'})

    try:
        user = get_user_by_email(email)
        if user:
            user_id, created_at = user[0], user[6] if len(user) > 6 else 'Unbekannt'

            # Get user profiles
            with get_db_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, type, array_length(ci_list, 1) as ci_count,
                           email_notifications, created_at
                    FROM notification_profiles
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                profiles = cur.fetchall()

            # Create user info display
            user_info = html.Div([
                html.H5(f'Benutzer gefunden: {email}'),
                html.P(f'User ID: {user_id}'),
                html.P(f'Erstellt: {created_at}'),
                html.P(f'Profile: {len(profiles)}'),

                # Show profiles
                html.Div([
                    html.H6('Profile:'),
                    html.Ul([
                        html.Li(f'{p[1]} ({p[2]}) - {p[3] or 0} CIs, {"E-Mail" if p[4] else "Apprise"}')
                        for p in profiles
                    ]) if profiles else html.P('Keine Profile')
                ]),

                # Delete user button
                html.Button(
                    f'Benutzer {email} löschen',
                    id={'type': 'delete-user', 'email': email},
                    n_clicks=0,
                    style=get_button_style('danger')
                ),
                dcc.ConfirmDialog(
                    id='confirm-delete-user',
                    message=f'Soll der Benutzer {email} mit allen Profilen gelöscht werden?'
                ),
                html.Div(id='delete-user-status', style={'marginTop': '10px'})
            ], style={
                'border': '1px solid #ddd',
                'borderRadius': '8px',
                'padding': '15px',
                'backgroundColor': '#f8f9fa'
            })

            return user_info
        else:
            return html.P(f'Benutzer "{email}" nicht gefunden.', style={'color': '#e74c3c'})

    except Exception as e:
        return html.P(f'Fehler bei der Suche: {str(e)}', style={'color': '#e74c3c'})

# Callback: Load all users list
@callback(
    Output('all-users-list', 'children'),
    [Input('refresh-users-btn', 'n_clicks'),
     Input('auth-status', 'data')],
    prevent_initial_call=False
)
def load_all_users(refresh_clicks, auth_data):
    """Load list of all users"""
    if not auth_data or not auth_data.get('authenticated'):
        return html.Div()

    if not is_admin_user(auth_data.get('email', '')):
        return html.Div()

    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.created_at,
                       COUNT(p.id) as profile_count,
                       MAX(p.updated_at) as last_activity
                FROM users u
                LEFT JOIN notification_profiles p ON u.id = p.user_id
                GROUP BY u.id, u.created_at
                ORDER BY u.created_at DESC
                LIMIT 50
            """)
            users_data = cur.fetchall()

        if not users_data:
            return html.P('Keine Benutzer gefunden.')

        # Create users table
        users_list = html.Div([
            html.P(f'Zeige {len(users_data)} Benutzer (max. 50):'),
            html.Table([
                html.Thead([
                    html.Tr([
                        html.Th('User ID'),
                        html.Th('Erstellt'),
                        html.Th('Profile'),
                        html.Th('Letzte Aktivität'),
                        html.Th('Aktionen')
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(str(user[0])[:8] + '...'),
                        html.Td(str(user[1])[:16] if user[1] else 'Unbekannt'),
                        html.Td(str(user[2])),
                        html.Td(str(user[3])[:16] if user[3] else 'Keine'),
                        html.Td(html.Button(
                            'Löschen',
                            id={'type': 'delete-user-by-id', 'user_id': str(user[0])},
                            n_clicks=0,
                            style={**get_button_style('danger'), 'padding': '5px 10px', 'fontSize': '12px'}
                        ))
                    ]) for user in users_data
                ])
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'border': '1px solid #ddd'
            })
        ])

        return users_list

    except Exception as e:
        return html.P(f'Fehler beim Laden der Benutzerliste: {str(e)}', style={'color': '#e74c3c'})
