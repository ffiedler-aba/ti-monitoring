import dash
from dash import Dash, html, dcc, Input, Output, callback
from mylibrary import *
import yaml
import os
import functools
import time
from flask import jsonify, request
import psutil
import gc

# Run idempotent DB migrations on startup
try:
    run_db_migrations()
except Exception as _e:
    # Avoid blocking startup; errors will be visible in logs
    print(f"DB migration warning: {_e}")

app = Dash(__name__, use_pages=True, title='TI-Monitoring', suppress_callback_exceptions=True)
server = app.server

# Add local CSS for Material Icons

# Configuration cache with size limit
_config_cache = {}
_config_cache_timestamp = 0
_config_cache_ttl = 300  # 5 seconds cache TTL
_config_cache_max_size = 10  # Limit cache size

# Layout cache with size limit
_layout_cache = {}
_layout_cache_timestamp = 0
_layout_cache_ttl = 60  # 1 minute cache TTL
_layout_cache_max_size = 5  # Limit cache size

def load_config():
    """Load configuration from YAML file with caching"""
    global _config_cache, _config_cache_timestamp
    
    current_time = time.time()
    if (not _config_cache or 
        current_time - _config_cache_timestamp > _config_cache_ttl):
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                _config_cache = yaml.safe_load(f) or {}
            _config_cache_timestamp = current_time
            
            # Limit cache size
            if len(_config_cache) > _config_cache_max_size:
                # Keep only the most recent entries
                keys = list(_config_cache.keys())[:_config_cache_max_size]
                _config_cache = {k: _config_cache[k] for k in keys}
        except (FileNotFoundError, Exception):
            _config_cache = {}
            _config_cache_timestamp = current_time
    
    return _config_cache

def load_footer_config():
    """Load footer configuration from cached config"""
    config = load_config()
    return config.get('footer', {})

def load_core_config():
    """Load core configuration from cached config"""
    config = load_config()
    return config.get('core', {})

def load_header_config():
    """Load header configuration from cached config"""
    core_config = load_core_config()
    return core_config.get('header', {})

def create_footer_element(config_item):
    """Create a footer element based on configuration"""
    if not config_item.get('enabled', True):
        return None
    
    if 'text' in config_item:  # Copyright element
        return html.Div(config_item['text'])
    
    # Link element
    link_attrs = {'href': config_item['link']}
    if config_item.get('new_tab', False):
        link_attrs['target'] = '_blank'
    
    return html.Div([html.A(config_item['label'], **link_attrs)])

def build_footer_elements(footer_config):
    """Build footer elements efficiently"""
    footer_elements = []
    
    # Pre-define footer sections for faster iteration
    footer_sections = ['home', 'documentation', 'privacy', 'imprint', 'copyright']
    
    for section in footer_sections:
        if section in footer_config:
            element = create_footer_element(footer_config[section])
            if element:
                footer_elements.append(element)
    
    return footer_elements

def serve_layout():
    # Check layout cache first
    global _layout_cache, _layout_cache_timestamp
    
    current_time = time.time()
    if (not _layout_cache or 
        current_time - _layout_cache_timestamp > _layout_cache_ttl):
        
        # Load configurations (now cached)
        footer_config = load_footer_config()
        core_config = load_core_config()
        header_config = load_header_config()
        
        # home_url entfernt – Logo-Link führt auf Startseite
        app_home_url = '/'
        
        # Get header configurations
        header_title = header_config.get('title', 'TI-Monitoring')
        logo_config = header_config.get('logo', {})
        logo_path = logo_config.get('path', 'assets/logo.svg')
        logo_alt = logo_config.get('alt', 'Logo')
        logo_height = logo_config.get('height', 50)
        logo_width = logo_config.get('width', 50)
        
        # Build footer elements efficiently
        footer_elements = build_footer_elements(footer_config)
        
        # Get home page content
        try:
            from pages.home import serve_layout as home_layout
            home_content = home_layout()
        except Exception as e:
            home_content = html.Div([
                html.P('Fehler beim Laden der Home-Seite.'),
                html.P(f'Fehler: {str(e)}')
            ])
        
        # Create layout
        _layout_cache = html.Div([
            html.Header(children = [
                html.Div(children=[
                    html.Div(id='logo-wrapper', children = [
                        html.A(href=app_home_url, children = [
                            html.Img(id='logo', src=logo_path, alt=logo_alt, height=logo_height, width=logo_width)
                        ])
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}),
                    html.H1(children=header_title, style={'margin': '0', 'fontSize': '1.6rem'})
                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '16px'}),
                # Hamburger-Menü (rechts)
                html.Div(children=[
                    html.Details(children=[
                        html.Summary(
                            html.I(className='material-icons', children='menu'),
                            style={'listStyle': 'none', 'cursor': 'pointer', 'padding': '6px 8px', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'}
                        ),
                        html.Div(id='hamburger-menu-content', children=[
                            html.A(
                                [
                                    html.Span(html.I(className='material-icons', children='home'), style={'marginRight': '10px'}),
                                    html.Span('Start')
                                ],
                                href='/',
                                style={'display': 'flex', 'alignItems': 'center', 'padding': '10px 12px', 'textDecoration': 'none', 'color': '#2c3e50', 'borderRadius': '6px'}
                            ),
                            html.A(
                                [
                                    html.Span(html.I(className='material-icons', children='analytics'), style={'marginRight': '10px'}),
                                    html.Span('Statistiken')
                                ],
                                href='/stats',
                                style={'display': 'flex', 'alignItems': 'center', 'padding': '10px 12px', 'textDecoration': 'none', 'color': '#2c3e50', 'borderRadius': '6px'}
                            ),
                            html.A(
                                [
                                    html.Span(html.I(className='material-icons', children='notifications'), style={'marginRight': '10px'}),
                                    html.Span('Benachrichtigungen')
                                ],
                                href='/notifications',
                                style={'display': 'flex', 'alignItems': 'center', 'padding': '10px 12px', 'textDecoration': 'none', 'color': '#2c3e50', 'borderRadius': '6px'}
                            ),
                            # Admin link (hidden by default, shown for admin users)
                            html.A(
                                [
                                    html.Span(html.I(className='material-icons', children='admin_panel_settings'), style={'marginRight': '10px'}),
                                    html.Span('Admin')
                                ],
                                href='/admin',
                                id='admin-menu-link',
                                style={'display': 'none', 'alignItems': 'center', 'padding': '10px 12px', 'textDecoration': 'none', 'color': '#e74c3c', 'borderRadius': '6px'}
                            )
                        ], style={'position': 'absolute', 'right': '0', 'marginTop': '8px', 'background': '#ffffff', 'border': '1px solid #e0e0e0', 'borderRadius': '10px', 'padding': '8px', 'boxShadow': '0 8px 24px rgba(0,0,0,0.12)', 'minWidth': '220px', 'display': 'grid', 'rowGap': '4px'})
                    ], style={'position': 'relative'})
                ], style={'marginLeft': 'auto'})
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '16px', 'padding': '8px 12px'}),
            html.Main(children = [
                html.Div(id='page-container', children=[
                    dcc.Loading(
                        id = 'spinner',
                        overlay_style = {"visibility":"visible", "filter": "blur(2px)"},
                        type = "circle",
                        children = [dash.page_container]
                    )
                ]),
                html.Div(className = 'box', children = [
                    html.H3('Disclaimer'),
                    html.Span('Die Bereitstellung der abgebildeten Informationen erfolgt ohne Gewähr. Als Grundlage dienen Daten der gematik GmbH, die sich über eine öffentlich erreichbare Schnittstelle abrufen lassen. Weitere Informationen dazu hier: '),
                    html.A('https://github.com/gematik/api-tilage', href='https://github.com/gematik/api-tilage', target='_blank'),
                    html.Span('.')
                ]),
            ]),
            html.Div(id = 'footer', children = footer_elements),
            
            # Global auth status store (used across all pages)
            dcc.Store(id='auth-status', storage_type='local')
        ])
        
        _layout_cache_timestamp = current_time
        
        # Force garbage collection periodically
        if int(current_time) % 300 == 0:  # Every 5 minutes
            gc.collect()
    
    return _layout_cache

# This is the correct way to set the layout - it should be the function itself, not the result of calling it
app.layout = serve_layout

# Health check endpoint
@server.route('/health')
def health_check():
    """Health check endpoint for monitoring the application status"""
    try:
        # Check configuration loading
        config_status = "healthy"
        config_error = None
        try:
            config = load_config()
            if not config:
                config_status = "warning"
                config_error = "Empty configuration"
        except Exception as e:
            config_status = "unhealthy"
            config_error = str(e)
        
        # Check layout generation
        layout_status = "healthy"
        layout_error = None
        try:
            layout = serve_layout()
            if not layout:
                layout_status = "warning"
                layout_error = "Empty layout"
        except Exception as e:
            layout_status = "unhealthy"
            layout_error = str(e)
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Database health
        db_status = "healthy"
        db_error = None
        try:
            with get_db_conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
        
        # Overall health status
        overall_status = "healthy"
        if config_status == "unhealthy" or layout_status == "unhealthy":
            overall_status = "unhealthy"
        elif config_status == "warning" or layout_status == "warning":
            overall_status = "warning"
        
        health_data = {
            "status": overall_status,
            "timestamp": time.time(),
            "uptime": time.time() - _config_cache_timestamp if _config_cache_timestamp > 0 else 0,
            "components": {
                "configuration": {
                    "status": config_status,
                    "error": config_error,
                    "cache_age": time.time() - _config_cache_timestamp if _config_cache_timestamp > 0 else None,
                    "cache_ttl": _config_cache_ttl
                },
                "layout": {
                    "status": layout_status,
                    "error": layout_error,
                    "cache_age": time.time() - _layout_cache_timestamp if _layout_cache_timestamp > 0 else None,
                    "cache_ttl": _layout_cache_ttl
                },
                "database": {
                    "status": db_status,
                    "error": db_error
                }
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "memory_total": memory.total
            }
        }
        
        status_code = 200 if overall_status == "healthy" else (503 if overall_status == "unhealthy" else 200)
        return jsonify(health_data), status_code
        
    except Exception as e:
        error_data = {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": f"Health check failed: {str(e)}"
        }
        return jsonify(error_data), 503

# Unsubscribe endpoint
@server.route('/unsubscribe/<token>')
def unsubscribe(token):
    """Unsubscribe endpoint.

    - Ohne Query-Param entfernt der Endpoint das gesamte Profil (Bestand).
    - Mit Query-Param u=<hash> wird nur die einzelne Apprise-URL am Hash gelöscht.
    """
    try:
        # Query-Param für per-URL-Opt-Out
        url_hash = request.args.get('u')
        
        # Get profile by token
        profile = get_profile_by_unsubscribe_token(token)
        if not profile:
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Ungültiger Link</title></head>
            <body>
                <h2>Ungültiger Link</h2>
                <p>Der von Ihnen aufgerufene Link ist ungültig oder wurde bereits verwendet.</p>
            </body>
            </html>
            ''', 404
        
        profile_id, user_id, name, email_notifications, email_address = profile

        # Per-URL-Opt-Out
        if url_hash:
            if remove_apprise_url_by_token_and_hash(token, url_hash):
                return f'''
                <!DOCTYPE html>
                <html>
                <head><title>Kanal abgemeldet</title></head>
                <body>
                    <h2>Kanal abgemeldet</h2>
                    <p>Die ausgewählte Benachrichtigungs‑URL wurde erfolgreich aus dem Profil "{name}" entfernt.</p>
                    <p>Sie können die übrigen Kanäle in den <a href="/notifications">Benachrichtigungseinstellungen</a> verwalten.</p>
                </body>
                </html>
                ''', 200
            else:
                return '''
                <!DOCTYPE html>
                <html>
                <head><title>Nichts zu entfernen</title></head>
                <body>
                    <h2>Nichts zu entfernen</h2>
                    <p>Die angegebene URL konnte nicht gefunden werden. Der Link ist möglicherweise abgelaufen oder bereits verwendet.</p>
                </body>
                </html>
                ''', 404

        # Profil-Opt-Out (Bestand)
        if delete_profile_by_unsubscribe_token(token):
            return f'''
            <!DOCTYPE html>
            <html>
            <head><title>Abmeldung erfolgreich</title></head>
            <body>
                <h2>Abmeldung erfolgreich</h2>
                <p>Das Benachrichtigungsprofil "{name}" wurde erfolgreich gelöscht.</p>
                <p>Sie erhalten keine weiteren Benachrichtigungen von diesem Profil.</p>
            </body>
            </html>
            ''', 200
        else:
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Fehler bei der Abmeldung</title></head>
            <body>
                <h2>Fehler bei der Abmeldung</h2>
                <p>Beim Löschen des Profils ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut.</p>
            </body>
            </html>
            ''', 500
            
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>Fehler</title></head>
        <body>
            <h2>Fehler</h2>
            <p>Ein Fehler ist aufgetreten: {str(e)}</p>
        </body>
        </html>
        ''', 500

# API endpoint for requesting OTP
@server.route('/api/auth/otp/request', methods=['POST'])
def request_otp():
    """Request OTP for email"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'E-Mail-Adresse ist erforderlich'}), 400
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Ungültige E-Mail-Adresse'}), 400
        
        # Check if user exists, create if not
        user = get_user_by_email(email)
        if user:
            user_id = user[0]
        else:
            user_id = create_user(email)
        
        if not user_id:
            return jsonify({'error': 'Fehler beim Erstellen des Benutzers'}), 500
        
        # Generate OTP
        otp, otp_id = generate_otp_for_user(user_id, request.remote_addr)
        
        if not otp or not otp_id:
            return jsonify({'error': 'Fehler beim Generieren des OTP-Codes'}), 500
        
        # Send OTP via Apprise (using the template from config)
        config = load_config()
        otp_template = config.get('core', {}).get('otp_apprise_url_template')
        
        if not otp_template:
            return jsonify({'error': 'OTP-Template nicht konfiguriert'}), 500
        
        # Debug: Check values before formatting
        print(f"Debug: email={email}, otp={otp}, template={otp_template}")
        
        # Ensure email and otp are strings
        if not email or not otp:
            return jsonify({'error': 'E-Mail oder OTP ist leer'}), 500
        
        try:
            # Format the template with user email and OTP
            apprise_url = otp_template.format(email=str(email), otp=str(otp))
            
            # Send OTP notification
            apobj = apprise.Apprise()
            apobj.add(apprise_url)
            apobj.notify(
                title='TI-Monitoring OTP-Code',
                body=f'Ihr OTP-Code für TI-Monitoring lautet: {otp}\n\nDieser Code ist 10 Minuten gültig.',
                body_format=apprise.NotifyFormat.TEXT
            )
        except Exception as e:
            return jsonify({'error': f'Fehler beim Formatieren der Apprise-URL: {str(e)}'}), 500
        
        return jsonify({'message': 'OTP-Code wurde gesendet'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Fehler beim Senden des OTP-Codes: {str(e)}'}), 500

# API endpoint for validating OTP
@server.route('/api/auth/otp/validate', methods=['POST'])
def validate_otp_api():
    """Validate OTP code"""
    try:
        data = request.get_json()
        email = data.get('email')
        otp_code = data.get('otp')
        
        if not email or not otp_code:
            return jsonify({'error': 'E-Mail und OTP-Code sind erforderlich'}), 400
        
        # Get user by email
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'Benutzer nicht gefunden'}), 404
        
        user_id = user[0]
        
        # Check if account is locked
        if is_account_locked(user_id):
            return jsonify({'error': 'Konto ist gesperrt. Bitte versuchen Sie es später erneut.'}), 423
        
        # Validate OTP
        if validate_otp(user_id, otp_code):
            # Authentication successful
            return jsonify({
                'message': 'Authentifizierung erfolgreich',
                'user_id': user_id,
                'email': email
            }), 200
        else:
            # OTP validation failed
            # Check if we should lock the account
            with get_db_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT failed_login_attempts FROM users WHERE id = %s
                """, (user_id,))
                failed_attempts = cur.fetchone()[0] if cur.fetchone() else 0
                
                if failed_attempts >= 5:
                    lock_user_account(user_id)
                    return jsonify({'error': 'Zu viele fehlgeschlagene Versuche. Konto ist jetzt gesperrt.'}), 423
            
            return jsonify({'error': 'Ungültiger OTP-Code'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Fehler bei der Verifizierung: {str(e)}'}), 500

# API endpoint for logout
@server.route('/api/auth/logout', methods=['POST'])
def logout():
    """End user session"""
    # In a session-based implementation, we would clear the session here
    # For now, we just return a success message
    return jsonify({'message': 'Erfolgreich abgemeldet'}), 200

# API endpoint for listing user profiles
@server.route('/api/profiles', methods=['GET'])
def list_profiles():
    """List user profiles"""
    # In a real implementation, we would check authentication here
    # For now, we'll just return an empty list
    return jsonify([]), 200

# Callback to show/hide admin link in hamburger menu
@callback(
    Output('admin-menu-link', 'style'),
    [Input('auth-status', 'data')],
    prevent_initial_call=False
)
def toggle_admin_menu_link(auth_data):
    """Show admin link only for authenticated admin users"""
    if not auth_data or not auth_data.get('authenticated'):
        return {'display': 'none'}
    
    user_email = auth_data.get('email', '')
    if is_admin_user(user_email):
        return {'display': 'flex', 'alignItems': 'center', 'padding': '10px 12px', 'textDecoration': 'none', 'color': '#e74c3c', 'borderRadius': '6px'}
    else:
        return {'display': 'none'}

if __name__ == '__main__':
    app.run(debug=False)