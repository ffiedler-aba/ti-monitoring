import dash
from dash import html, dcc, Input, Output, callback, no_update
from mylibrary import is_admin_user

def create_admin_header(title):
    """Create consistent admin header with logo"""
    return html.Header([
        html.Div([
            html.Div(id='logo-wrapper', children=[
                html.A(href='/', children=[
                    html.Img(id='logo', src='/assets/logo.svg', alt='TI-Monitoring Logo', height=50, width=50)
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}),
            html.H1(title, style={
                'margin': '0',
                'fontSize': '1.6rem',
                'color': '#2c3e50'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '16px'})
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'marginBottom': '30px',
        'borderBottom': '2px solid #e74c3c',
        'paddingBottom': '10px'
    })

dash.register_page(__name__, path='/admin')

def serve_layout():
    """Admin dashboard layout"""
    layout = html.Div([
        # Header with logo
        create_admin_header('Admin Dashboard'),

        # Admin content (hidden until auth verified)
        html.Div(id='admin-root-content', children=[
            html.P('Überprüfe Admin-Berechtigung...', style={'textAlign': 'center'})
        ]),

        # Non-admin message (hidden by default)
        html.Div(id='admin-root-denied', children=[
            html.H3('Zugriff verweigert'),
            html.P('Sie haben keine Admin-Berechtigung für diesen Bereich.'),
            html.A('Zurück zu Notifications', href='/notifications', className='btn btn-primary')
        ], style={'display': 'none'}),

        # Store for admin status
        dcc.Store(id='admin-root-auth-status'),

        # Check auth status from notifications page (same ID as notifications)
        dcc.Store(id='auth-status', storage_type='local')
    ])

    return layout

layout = serve_layout

# Define the callback logic without registering it yet
def _admin_check_access_callback(auth_data):
    """Check if user has admin access"""
    if not auth_data or not auth_data.get('authenticated'):
        return [
            html.Div([
                html.H3('Authentifizierung erforderlich'),
                html.P('Bitte melden Sie sich zuerst über die Notifications-Seite an.'),
                html.A('Zur Anmeldung', href='/notifications', className='btn btn-primary')
            ])
        ], {'display': 'none'}, {'admin': False}

    user_email = auth_data.get('email', '')
    if is_admin_user(user_email):
        admin_content = html.Div([
            html.H3(f'Willkommen, Admin ({user_email})'),
            html.P('Admin-Dashboard wird geladen...'),
            html.Hr(),
            html.H4('Navigation'),
            html.Ul([
                html.Li(html.A('System-Logs anzeigen', href='/admin/logs', style={'color': '#3498db'})),
                html.Li(html.A('Benutzer verwalten', href='/admin/users', style={'color': '#3498db'})),
                html.Li(html.A('Erweiterte Statistiken', href='/admin/stats', style={'color': '#3498db'}))
            ], style={'listStyle': 'none', 'padding': '0'})
        ])
        return admin_content, {'display': 'none'}, {'admin': True, 'email': user_email}
    else:
        return html.Div(), {'display': 'block'}, {'admin': False}


# Register callbacks separately to avoid duplicate output sets
try:
    app = dash.get_app()

    def _remove_existing_callbacks(target_outputs):
        try:
            cmap = getattr(app, 'callback_map', {}) or {}
            keys_to_delete = []
            for k, meta in list(cmap.items()):
                outputs = meta.get('outputs_list') or meta.get('outputs')
                names = []
                if isinstance(outputs, list):
                    for out in outputs:
                        if isinstance(out, dict) and 'id' in out and 'property' in out:
                            names.append(f"{out['id']}.{out['property']}")
                elif isinstance(outputs, dict):
                    names.append(f"{outputs.get('id')}.{outputs.get('property')}")
                match = (set(names) == set(target_outputs))
                if not match:
                    out_str = meta.get('output')
                    if isinstance(out_str, str):
                        parts = [p.strip() for p in out_str.split(',')]
                        match = (set(parts) == set(target_outputs))
                if match:
                    keys_to_delete.append(k)
            for k in keys_to_delete:
                try:
                    del app.callback_map[k]
                except Exception:
                    pass
        except Exception:
            pass

    # 1) Store-only callback
    _remove_existing_callbacks(['admin-root-auth-status.data'])
    app.callback(
        Output('admin-root-auth-status', 'data'),
        Input('auth-status', 'data'),
        prevent_initial_call=False
    )(_admin_compute_auth_status)

    # 2) UI callback based on store
    _remove_existing_callbacks(['admin-root-content.children', 'admin-root-denied.style'])
    app.callback(
        [Output('admin-root-content', 'children'),
         Output('admin-root-denied', 'style')],
        Input('admin-root-auth-status', 'data'),
        prevent_initial_call=False
    )(_admin_build_ui)
except Exception:
    # Fallback: do nothing if app not ready at import time
    pass
