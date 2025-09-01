import dash
from dash import html, dcc, Input, Output, State, callback, no_update, callback_context
import json
from mylibrary import *
from myconfig import *
import yaml
import os
import apprise

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

# Global variable to store authentication status (in production, use session or database)
auth_status = {'authenticated': False}

def serve_layout():
    layout = html.Div([
        html.H2('Notification Settings', style={
            'color': '#2c3e50',
            'fontWeight': '600',
            'marginBottom': '30px',
            'borderBottom': '2px solid #3498db',
            'paddingBottom': '10px'
        }),
        # Store for authentication status (persistent in browser)
        dcc.Store(id='auth-status', storage_type='local', data=auth_status),
        
        # Login form (shown when not authenticated)
        html.Div(id='login-container', children=[
            html.H3('Login Required', style={'color': '#2c3e50', 'marginBottom': '20px'}),
            html.P('Please enter the password to access notification settings.', style={'color': '#7f8c8d', 'marginBottom': '20px'}),
            dcc.Input(
                id='password-input',
                type='password',
                placeholder='Enter password',
                style={
                    'width': '100%', 
                    'marginBottom': '15px',
                    'padding': '12px',
                    'border': '2px solid #e9ecef',
                    'borderRadius': '8px',
                    'fontSize': '14px',
                    'transition': 'border-color 0.3s ease'
                }
            ),
            html.Button('Login', id='login-button', n_clicks=0, style=get_button_style('primary')),
            html.Div(id='login-error', style={'color': '#e74c3c', 'marginTop': '15px', 'fontWeight': '500'})
        ], style={
            'maxWidth': '400px',
            'margin': '0 auto',
            'padding': '30px',
            'backgroundColor': 'white',
            'borderRadius': '12px',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'
        }),
        
        # Settings interface (hidden when not authenticated)
        html.Div(id='settings-container', children=[
            html.P('Manage your notification profiles below.', style={
                'color': '#7f8c8d',
                'fontSize': '16px',
                'marginBottom': '25px'
            }),
            
            # Display existing profiles
            html.Div(id='profiles-container'),
            
            # Add new profile button
            html.Button('Add New Profile', id='add-profile-button', n_clicks=0, style=get_button_style('success')),
            
            # Profile form (hidden by default)
            html.Div(id='profile-form-container', children=[
                html.H3('Profile Details', style={
                    'color': '#2c3e50',
                    'marginBottom': '20px',
                    'borderBottom': '2px solid #3498db',
                    'paddingBottom': '10px'
                }),
                dcc.Store(id='editing-profile-index'),
                dcc.Store(id='available-cis-data'),
                dcc.Store(id='selected-cis-data', data=[]),
                dcc.Input(
                    id='profile-name-input',
                    placeholder='Profile Name',
                    style={
                        'width': '100%', 
                        'marginBottom': '15px',
                        'padding': '12px',
                        'border': '2px solid #e9ecef',
                        'borderRadius': '8px',
                        'fontSize': '14px',
                        'transition': 'border-color 0.3s ease'
                    }
                ),
                html.Div([
                    html.Label('Notification Type:', style={
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
                        style={'marginBottom': '15px'}
                    )
                ], style={'marginBottom': '15px'}),
                html.Div([
                    html.Label('Configuration Items:', style={
                        'display': 'block',
                        'marginBottom': '10px',
                        'fontWeight': '500',
                        'color': '#2c3e50'
                    }),
                    html.Div(id='ci-checkboxes-container', style={
                        'maxHeight': '200px',
                        'overflowY': 'auto',
                        'border': '2px solid #e9ecef',
                        'borderRadius': '8px',
                        'padding': '15px',
                        'backgroundColor': '#f8f9fa'
                    })
                ], style={'marginBottom': '15px'}),
                dcc.Textarea(
                    id='apprise-urls-textarea',
                    placeholder='Apprise URLs (one per line)',
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
                        'transition': 'border-color 0.3s ease'
                    }
                ),
                html.Div(id='form-error', style=get_error_style(visible=False)),
                html.Div([
                    html.Button('Save Profile', id='save-profile-button', n_clicks=0, style=get_button_style('success')),
                    html.Button('Cancel', id='cancel-profile-button', n_clicks=0, style=get_button_style('secondary'))
                ], style={'display': 'flex', 'gap': '10px'})
            ], style={
                'display': 'none',
                'backgroundColor': 'white',
                'padding': '25px',
                'borderRadius': '12px',
                'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                'marginTop': '20px',
                'border': '1px solid #e9ecef'
            }),
            
            # Delete confirmation modal
            dcc.ConfirmDialog(
                id='delete-confirm',
                message='Are you sure you want to delete this profile?'
            ),
            # Test Apprise notification button
            html.Div([
                html.H3('Test Apprise Notification', style={
                    'color': '#2c3e50',
                    'marginBottom': '15px',
                    'borderBottom': '2px solid #3498db',
                    'paddingBottom': '10px'
                }),
                html.P('Enter an Apprise URL to test if your notification system is working.', style={
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
                        'transition': 'border-color 0.3s ease'
                    }
                ),
                html.Button('Test Notification', id='test-notification-button', n_clicks=0, style=get_button_style('warning')),
                html.Div(id='test-result', style={'marginTop': '15px'})
            ], style={
                'marginTop': '30px', 
                'padding': '25px', 
                'border': '1px solid #e9ecef', 
                'borderRadius': '12px',
                'backgroundColor': 'white',
                'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.05)'
            })
        ], style={'display': 'none'})
    ], style={
        'maxWidth': '800px',
        'margin': '0 auto',
        'padding': '20px',
        'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    })
    
    return layout

layout = serve_layout

# Callback to handle login
@callback(
    [Output('login-container', 'style'),
     Output('settings-container', 'style'),
     Output('login-error', 'children'),
     Output('auth-status', 'data')],
    [Input('login-button', 'n_clicks')],
    [State('password-input', 'value'),
     State('auth-status', 'data')]
)
def handle_login(n_clicks, password, auth_data):
    if n_clicks and n_clicks > 0:
        if password:
            if validate_password(password):
                auth_data['authenticated'] = True
                return [{'display': 'none'}, {'display': 'block'}, '', auth_data]
            else:
                return [no_update, no_update, 'Invalid password. Please try again.', auth_data]
        else:
            return [no_update, no_update, 'Please enter a password.', auth_data]
    return [no_update, no_update, '', auth_data]



# Callback to handle Enter key in password input
@callback(
    Output('login-button', 'n_clicks'),
    [Input('password-input', 'n_submit')],
    [State('login-button', 'n_clicks')]
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
        # Load core configurations
        core_config = load_core_config()
        config_file = core_config.get('file_name') or 'data/data.hdf5'
        
        # Get all CIs from the data file
        from mylibrary import get_data_of_all_cis
        cis_df = get_data_of_all_cis(config_file)
        
        if not cis_df.empty:
            # Convert to list of dictionaries with ci and name
            cis_list = []
            for _, row in cis_df.iterrows():
                ci_info = {
                    'ci': str(row.get('ci', '')),
                    'name': str(row.get('name', '')),
                    'organization': str(row.get('organization', '')),
                    'product': str(row.get('product', ''))
                }
                cis_list.append(ci_info)
            return cis_list
        else:
            return []
    except Exception as e:
        print(f"Error loading CIs: {e}")
        return []

# Callback to render CI checkboxes
@callback(
    Output('ci-checkboxes-container', 'children'),
    [Input('available-cis-data', 'data'),
     Input('editing-profile-index', 'data')],
    [State('auth-status', 'data')]
)
def render_ci_checkboxes(cis_data, editing_index, auth_data):
    if not auth_data or not auth_data.get('authenticated', False) or not cis_data:
        return html.P('Loading CIs...', style={'color': '#7f8c8d', 'textAlign': 'center'})
    
    try:
        # Load existing profile data if editing
        selected_cis = []
        if editing_index is not None:
            core_config = load_core_config()
            config_file = core_config.get('notifications_config_file') or notifications_config_file
            config = get_notification_config(config_file)
            if 0 <= editing_index < len(config):
                selected_cis = config[editing_index].get('ci_list', [])
        
        # Create checkboxes for each CI
        checkbox_children = []
        for ci_info in cis_data:
            ci_id = ci_info.get('ci', '')
            ci_name = ci_info.get('name', '')
            ci_org = ci_info.get('organization', '')
            ci_product = ci_info.get('product', '')
            
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
    Output('selected-cis-data', 'data', allow_duplicate=True),
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
        # Form is opened for editing, load existing selection
        try:
            core_config = load_core_config()
            config_file = core_config.get('notifications_config_file') or notifications_config_file
            config = get_notification_config(config_file)
            if 0 <= editing_index < len(config):
                return config[editing_index].get('ci_list', [])
        except Exception:
            pass
    return []

# Callback to collect selected CIs from checkboxes
@callback(
    Output('selected-cis-data', 'data'),
    [Input({'type': 'ci-checkbox', 'ci': dash.ALL}, 'value')],
    [State('available-cis-data', 'data')],
    prevent_initial_call=True
)
def update_selected_cis(checkbox_values, available_cis_data):
    """Update the selected CIs when checkboxes change"""
    if not available_cis_data:
        return []
    
    # Collect all selected CIs from the checkbox values
    selected_cis = []
    for checkbox_value in checkbox_values:
        if checkbox_value:  # If checkbox has a value (is checked)
            selected_cis.extend(checkbox_value)
    
    # Remove duplicates
    selected_cis = list(set(selected_cis))
    
    return selected_cis

# Callback to load and display profiles
@callback(
    Output('profiles-container', 'children'),
    [Input('auth-status', 'data'),
     Input('save-profile-button', 'n_clicks'),
     Input('delete-confirm', 'submit_n_clicks')]
)
def display_profiles(auth_data, save_clicks, delete_clicks):
    if not auth_data.get('authenticated', False):
        return []
    
    # Load core configurations
    core_config = load_core_config()
    config_notifications_config_file = core_config.get('notifications_config_file') or notifications_config_file
    
    try:
        config = get_notification_config(config_notifications_config_file)
        if not config:
            return html.P('No notification profiles found. Add a new profile to get started.')
        
        profile_cards = []
        for i, profile in enumerate(config):
            # Count items
            ci_count = len(profile.get('ci_list', []))
            url_count = len(profile.get('apprise_urls', []))
            
            card = html.Div([
                html.H4(profile.get('name', 'Unnamed Profile'), style={
                    'color': '#2c3e50',
                    'marginBottom': '15px',
                    'fontWeight': '600',
                    'borderBottom': '1px solid #ecf0f1',
                    'paddingBottom': '10px'
                }),
                html.Div([
                    html.P(f"Type: {profile.get('type', 'whitelist').title()}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    }),
                    html.P(f"Configuration Items: {ci_count}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    }),
                    html.P(f"Notification URLs: {url_count}", style={
                        'color': '#7f8c8d',
                        'margin': '5px 0',
                        'fontSize': '14px'
                    })
                ], style={'marginBottom': '20px'}),
                html.Div([
                    html.Button('Edit', id={'type': 'edit-profile', 'index': i}, n_clicks=0, style=get_button_style('secondary')),
                    html.Button('Delete', id={'type': 'delete-profile', 'index': i}, n_clicks=0, 
                               style=get_button_style('danger'))
                ], style={'display': 'flex', 'gap': '10px'})
            ], className='profile-card', style={
                'backgroundColor': 'white',
                'padding': '25px',
                'borderRadius': '12px',
                'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.1)',
                'marginBottom': '20px',
                'border': '1px solid #e9ecef',
                'transition': 'transform 0.2s ease, box-shadow 0.2s ease'
            })
            
            profile_cards.append(card)
        
        return profile_cards
    except Exception as e:
        return html.P(f'Error loading profiles: {str(e)}')

# Callback to show profile form
@callback(
    [Output('profile-form-container', 'style'),
     Output('editing-profile-index', 'data'),
     Output('profile-name-input', 'value'),
     Output('notification-type-radio', 'value'),
     Output('apprise-urls-textarea', 'value')],
    [Input('add-profile-button', 'n_clicks'),
     Input({'type': 'edit-profile', 'index': dash.ALL}, 'n_clicks')],
    [State('auth-status', 'data')]
)
def show_profile_form(add_clicks, edit_clicks, auth_data):
    if not auth_data.get('authenticated', False):
        return [{'display': 'none'}, None, '', 'whitelist', '']
    
    # Check if add button was clicked
    ctx = callback_context
    if not ctx.triggered:
        return [{'display': 'none'}, None, '', 'whitelist', '']
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'add-profile-button':
        # Show empty form for new profile
        return [{'display': 'block'}, None, '', 'whitelist', '']
    else:
        # Show form with existing profile data for editing
        try:
            button_data = json.loads(button_id.replace("'", '"'))
            index = button_data['index']
            
            # Load core configurations
            core_config = load_core_config()
            config_notifications_config_file = core_config.get('notifications_config_file') or notifications_config_file
            
            config = get_notification_config(config_notifications_config_file)
            if 0 <= index < len(config):
                profile = config[index]
                name = profile.get('name', '')
                notification_type = profile.get('type', 'whitelist')
                apprise_urls = '\n'.join(profile.get('apprise_urls', []))
                
                return [{'display': 'block'}, index, name, notification_type, apprise_urls]
        except Exception:
            pass
    
    return [{'display': 'none'}, None, '', 'whitelist', '']

# Callback to save profile
@callback(
    [Output('profile-form-container', 'style', allow_duplicate=True),
     Output('form-error', 'children'),
     Output('form-error', 'style'),
     Output('save-profile-button', 'n_clicks')],
    [Input('save-profile-button', 'n_clicks'),
     Input('cancel-profile-button', 'n_clicks')],
    [State('editing-profile-index', 'data'),
     State('profile-name-input', 'value'),
     State('notification-type-radio', 'value'),
     State('apprise-urls-textarea', 'value'),
     State('selected-cis-data', 'data'),
     State('auth-status', 'data')],
    prevent_initial_call=True
)
def handle_profile_form(save_clicks, cancel_clicks, edit_index, name, notification_type, apprise_urls, selected_cis, auth_data):
    # Check which button was clicked
    ctx = callback_context
    if not ctx.triggered:
        return [no_update, '', get_error_style(visible=False), 0]
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Handle cancel button
    if button_id == 'cancel-profile-button':
        return [{'display': 'none'}, '', get_error_style(visible=False), 0]
    
    # Handle save button
    if button_id == 'save-profile-button' and save_clicks > 0:
        # Validate inputs
        if not name:
            return [no_update, 'Profile name is required.', get_error_style(visible=True), 0]
        
        # Get selected CIs from the selected-cis-data store
        ci_items = selected_cis if selected_cis else []
        
        # Process Apprise URLs
        url_items = [url.strip() for url in apprise_urls.split('\n') if url.strip()]
        
        # Validate Apprise URLs
        if url_items and not validate_apprise_urls(url_items):
            return [no_update, 'One or more Apprise URLs are invalid.', get_error_style(visible=True), 0]
        
        # Create profile object
        profile = {
            'name': name,
            'type': notification_type,
            'ci_list': ci_items,
            'apprise_urls': url_items
        }
        
        try:
            # Load core configurations
            core_config = load_core_config()
            config_notifications_config_file = core_config.get('notifications_config_file') or notifications_config_file
            
            # Load existing config
            config = get_notification_config(config_notifications_config_file)
            
            if edit_index is not None and 0 <= edit_index < len(config):
                # Update existing profile
                config[edit_index] = profile
            else:
                # Add new profile
                config.append(profile)
            
            # Save config
            if save_notification_config(config_notifications_config_file, config):
                return [{'display': 'none'}, '', get_error_style(visible=False), 0]  # Hide form and reset clicks
            else:
                return [no_update, 'Error saving configuration.', get_error_style(visible=True), 0]
        except Exception as e:
            return [no_update, f'Error: {str(e)}', get_error_style(visible=True), 0]
    
    return [no_update, '', get_error_style(visible=False), 0]

# Callback to handle delete confirmation
@callback(
    [Output('delete-confirm', 'displayed'),
     Output('delete-confirm', 'message')],
    [Input({'type': 'delete-profile', 'index': dash.ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def show_delete_confirm(delete_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return [False, '']
    
    # Get the triggered input that caused this callback
    triggered_input = ctx.triggered[0]
    
    # Only show confirmation if a delete button was actually clicked (n_clicks > 0)
    if triggered_input['value'] <= 0:
        return [False, '']
    
    try:
        button_id = triggered_input['prop_id'].split('.')[0]
        button_data = json.loads(button_id.replace("'", '"'))
        index = button_data['index']
        
        # Load core configurations
        core_config = load_core_config()
        config_notifications_config_file = core_config.get('notifications_config_file') or notifications_config_file
        
        config = get_notification_config(config_notifications_config_file)
        if 0 <= index < len(config):
            profile_name = config[index].get('name', 'Unnamed Profile')
            message = f'Are you sure you want to delete the profile "{profile_name}"?'
            return [True, message]
    except Exception:
        pass
    
    return [False, '']

# Callback to delete profile
@callback(
    Output('delete-confirm', 'submit_n_clicks'),
    [Input('delete-confirm', 'submit_n_clicks')],
    [State('delete-confirm', 'triggered')],
    prevent_initial_call=True
)
def delete_profile(submit_n_clicks, triggered):
    if not triggered or submit_n_clicks == 0:
        return 0
    
    try:
        # Extract index from triggered data
        if isinstance(triggered, list) and len(triggered) > 0:
            trigger = triggered[0]
            if 'prop_id' in trigger:
                button_id = trigger['prop_id'].split('.')[0]
                # Fix the JSON parsing
                if button_id.startswith('{') and button_id.endswith('}'):
                    button_data = json.loads(button_id)
                else:
                    button_data = json.loads(button_id.replace("'", '"'))
                index = button_data['index']
                
                # Load core configurations
                core_config = load_core_config()
                config_notifications_config_file = core_config.get('notifications_config_file') or notifications_config_file
                
                # Load config
                config = get_notification_config(config_notifications_config_file)
                
                # Remove profile at index
                if 0 <= index < len(config):
                    config.pop(index)
                    
                    # Save updated config
                    save_notification_config(config_notifications_config_file, config)
    except Exception:
        pass
    
    return submit_n_clicks

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
        return html.Div('Authentication required.', style={'color': 'red'})
    
    if not apprise_url or not apprise_url.strip():
        return html.Div('Please enter an Apprise URL to test.', style={'color': 'orange'})
    
    try:
        # Create Apprise object and add the URL
        apobj = apprise.Apprise()
        
        # Add the URL and check if it was added successfully
        if not apobj.add(apprise_url.strip()):
            return html.Div([
                html.I(className='material-icons', children='error', style={'color': 'red', 'margin-right': '8px'}),
                html.Span('Invalid Apprise URL format. Please check the URL syntax.', style={'color': 'red'}),
                html.Br(),
                html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
                html.Br(),
                html.Br(),
                html.Span('Common Mattermost format: mmost://username:password@hostname/channel', style={'color': 'blue', 'font-size': '0.9em'}),
                html.Br(),
                html.Span('Example: mmost://user:pass@mattermost.medisoftware.org/channel', style={'color': 'blue', 'font-size': '0.9em'})
            ])
        
        # Send test notification
        result = apobj.notify(
            title='TI-Monitoring Test Notification',
            body='This is a test notification from TI-Monitoring. If you receive this, your Apprise configuration is working correctly!',
            body_format=apprise.NotifyFormat.TEXT
        )
        
        if result:
            return html.Div([
                html.I(className='material-icons', children='check_circle', style={'color': 'green', 'margin-right': '8px'}),
                html.Span('Test notification sent successfully! Check your notification destination.', style={'color': 'green'}),
                html.Br(),
                html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
                html.Br(),
                html.Span('Note: If you don\'t receive the message, check your Mattermost channel and bot permissions.', style={'color': 'blue', 'font-size': '0.9em'})
            ])
        else:
            return html.Div([
                html.I(className='material-icons', children='error', style={'color': 'red', 'margin-right': '8px'}),
                html.Span('Failed to send test notification. Please check your Apprise URL and configuration.', style={'color': 'red'}),
                html.Br(),
                html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
                html.Br(),
                html.Br(),
                html.Span('Common issues:', style={'color': 'orange', 'font-weight': 'bold'}),
                html.Br(),
                html.Span('• Check if the Mattermost server is accessible', style={'color': 'orange'}),
                html.Br(),
                html.Span('• Verify username/password credentials', style={'color': 'orange'}),
                html.Br(),
                html.Span('• Ensure the bot has permission to post in the channel', style={'color': 'orange'}),
                html.Br(),
                html.Span('• Check Mattermost server logs for errors', style={'color': 'orange'})
            ])
            
    except Exception as e:
        return html.Div([
            html.I(className='material-icons', children='error', style={'color': 'red', 'margin-right': '8px'}),
            html.Span(f'Error testing notification: {str(e)}', style={'color': 'red'}),
            html.Br(),
            html.Span(f'URL: {apprise_url.strip()}', style={'color': 'gray', 'font-size': '0.9em'}),
            html.Br(),
            html.Br(),
            html.Span('Try this format instead:', style={'color': 'blue', 'font-weight': 'bold'}),
            html.Br(),
            html.Span('mmost://username:password@mattermost.medisoftware.org/channel', style={'color': 'blue', 'font-family': 'monospace'})
        ])
        