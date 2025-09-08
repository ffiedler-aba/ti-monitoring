import dash
from dash import html, dcc, Input, Output, callback, no_update
from mylibrary import is_admin_user

dash.register_page(__name__, path='/admin')

def serve_layout():
    """Admin dashboard layout"""
    layout = html.Div([
        html.H1('Admin Dashboard', style={
            'color': '#2c3e50',
            'fontWeight': '600',
            'marginBottom': '30px',
            'borderBottom': '2px solid #e74c3c',
            'paddingBottom': '10px'
        }),
        
        # Admin content (hidden until auth verified)
        html.Div(id='admin-content', children=[
            html.P('Überprüfe Admin-Berechtigung...', style={'textAlign': 'center'})
        ]),
        
        # Non-admin message (hidden by default)
        html.Div(id='admin-denied', children=[
            html.H3('Zugriff verweigert'),
            html.P('Sie haben keine Admin-Berechtigung für diesen Bereich.'),
            html.A('Zurück zu Notifications', href='/notifications', className='btn btn-primary')
        ], style={'display': 'none'}),
        
        # Store for admin status
        dcc.Store(id='admin-auth-status'),
        
        # Check auth status from notifications page (same ID as notifications)
        dcc.Store(id='auth-status', storage_type='local')
    ])
    
    return layout

layout = serve_layout

# Callback: Check admin status based on auth data from notifications
@callback(
    [Output('admin-content', 'children'),
     Output('admin-denied', 'style'),
     Output('admin-auth-status', 'data')],
    [Input('auth-status', 'data')],
    prevent_initial_call=False
)
def check_admin_access(auth_data):
    """Check if user has admin access"""
    if not auth_data or not auth_data.get('authenticated'):
        # Not authenticated - redirect to notifications
        return [
            html.Div([
                html.H3('Authentifizierung erforderlich'),
                html.P('Bitte melden Sie sich zuerst über die Notifications-Seite an.'),
                html.A('Zur Anmeldung', href='/notifications', className='btn btn-primary')
            ])
        ], {'display': 'none'}, {'admin': False}
    
    user_email = auth_data.get('email', '')
    if is_admin_user(user_email):
        # User is admin - show admin content
        admin_content = html.Div([
            html.H3(f'Willkommen, Admin ({user_email})'),
            html.P('Admin-Dashboard wird geladen...'),
            html.Hr(),
            html.H4('Navigation'),
            html.Ul([
                html.Li(html.A('System-Logs anzeigen', href='/admin/logs', style={'color': '#3498db'})),
                html.Li(html.A('Benutzer verwalten', href='/admin/users', style={'color': '#3498db'})),
                html.Li('Erweiterte Statistiken (in Entwicklung)')
            ], style={'listStyle': 'none', 'padding': '0'})
        ])
        return admin_content, {'display': 'none'}, {'admin': True, 'email': user_email}
    else:
        # User is not admin
        return html.Div(), {'display': 'block'}, {'admin': False}
