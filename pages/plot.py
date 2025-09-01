import dash
from dash import html, dcc, Input, Output, callback
import plotly.express as px
from mylibrary import *
from myconfig import *
import yaml
import os
import pandas as pd
import numpy as np

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

dash.register_page(__name__)


def serve_layout(ci=None, hours=None, **other_unknown_query_strings):
    # Load core configurations
    core_config = load_core_config()
    
    # Get configurations from YAML as primary source, fallback to myconfig.py
    config_file_name = core_config.get('file_name') or file_name
    config_home_url = core_config.get('home_url') or home_url
    config_stats_delta_hours = core_config.get('stats_delta_hours') or stats_delta_hours
    
    # Use provided hours parameter or default from config
    selected_hours = int(hours) if hours is not None else config_stats_delta_hours
    
    # Handle case when ci is None (no query parameter provided)
    if ci is None:
        return html.Div([
            html.H2('Fehler: Keine Komponente angegeben'),
            html.P('Bitte geben Sie eine Komponenten-ID in der URL an, z.B. /plot?ci=12345'),
            html.A(href=config_home_url, children=[
                html.Button('Zurück zur Startseite', className='button')
            ])
        ])
    
    # Get CI info for display
    ci_info = get_data_of_ci(config_file_name, ci)
    
    layout = [
        html.H2('Verfügbarkeit der Komponente ' + str(ci)),
        html.H3(ci_info['product'].iloc[0] + ', ' + ci_info['name'].iloc[0] + ', ' + ci_info['organization'].iloc[0]),
        html.A(href=config_home_url, children = [
            html.Button('Zurück', className = 'button')
        ]),
        
        # Time range selector
        html.Div(className='box', children=[
            html.H3('Zeitraum auswählen'),
            html.Div(className='time-selector', children=[
                html.Label('Darstellungszeitraum (Stunden):'),
                dcc.Dropdown(
                    id='hours-dropdown',
                    options=[
                        {'label': '1 Stunde', 'value': 1},
                        {'label': '3 Stunden', 'value': 3},
                        {'label': '6 Stunden', 'value': 6},
                        {'label': '12 Stunden', 'value': 12},
                        {'label': '24 Stunden', 'value': 24},
                        {'label': '48 Stunden', 'value': 48},
                        {'label': '72 Stunden', 'value': 72},
                        {'label': '1 Woche', 'value': 168}
                    ],
                    value=selected_hours,
                    clearable=False,
                    style={'width': '200px', 'display': 'inline-block', 'margin-left': '10px'}
                ),
                html.Button('Aktualisieren', id='update-button', className='button', style={'margin-left': '10px'})
            ]),
            html.P('Der Standardwert von ' + str(config_stats_delta_hours) + ' Stunden kann über die config.yaml angepasst werden.', 
                   style={'font-size': '0.9rem', 'color': 'var(--gray-600)', 'margin-top': 'var(--spacing-sm)'})
        ]),
        
        # Statistics section
        html.Div(id='statistics', className='box'),
        
        # Plot section
        html.Div(id='plot-container', children=[
            dcc.Graph(id='availability-plot')
        ]),
        
        # Store for current CI and hours
        dcc.Store(id='ci-store', data=ci),
        dcc.Store(id='hours-store', data=selected_hours),
        
        # Location component for URL updates
        dcc.Location(id='url', refresh=False)
    ]
    return layout

layout = serve_layout

@callback(
    [Output('availability-plot', 'figure'),
     Output('statistics', 'children')],
    [Input('update-button', 'n_clicks'),
     Input('hours-dropdown', 'value')],
    [dash.State('ci-store', 'data')],
    prevent_initial_call=False
)
def update_plot_and_stats(n_clicks, selected_hours, ci):
    """Update plot and statistics based on selected time range"""
    # Load core configurations
    core_config = load_core_config()
    config_file_name = core_config.get('file_name') or file_name
    
    # Ensure selected_hours is valid
    if selected_hours is None or selected_hours <= 0:
        selected_hours = 12  # Default fallback
    
    # Calculate cutoff time
    cutoff = (pd.Timestamp.now() - pd.Timedelta(hours=selected_hours)).tz_localize(get_localzone())
    
    # Get data
    ci_data = get_availability_data_of_ci(config_file_name, ci)
    ci_data = ci_data[ci_data['times']>=cutoff]
    
    if ci_data.empty:
        # Return empty plot and message if no data
        empty_fig = px.scatter(title='Keine Daten verfügbar für den gewählten Zeitraum')
        return empty_fig, html.Div('Keine Daten verfügbar für den gewählten Zeitraum')
    
    # Calculate statistics
    number_of_values = len(ci_data['values'])
    mean_availability = np.mean(ci_data['values'].values)
    first_timestamp = ci_data['times'].iloc[0].strftime('%d.%m.%Y %H:%M:%S Uhr')
    last_timestamp = ci_data['times'].iloc[-1].strftime('%d.%m.%Y %H:%M:%S Uhr')
    
    # Prepare data for plot
    plot_data = ci_data.rename(columns={
        'times': 'Zeit',
        'values': 'Verfügbarkeit'
    })
    
    # Create custom colors
    custom_colors = ['red' if v == 0 else 'green' for v in plot_data['Verfügbarkeit']]
    
    # Create plot
    fig = px.scatter(
        plot_data,
        x='Zeit',
        y='Verfügbarkeit',
        title=f'Verfügbarkeit der letzten {selected_hours} Stunden'
    )
    fig.update_traces(marker=dict(color=custom_colors))
    fig.update_yaxes(tickvals=[0, 1], ticktext=['0', '1'])
    fig.update_layout(yaxis=dict(range=[-0.1, 1.1]))
    
    # Create statistics
    stats = html.Div(className='box', children=[
        html.H3('Statistik'),
        html.Ul([
            html.Li(f'Anzahl der Werte: {number_of_values}'),
            html.Li(f'Erster Wert: {first_timestamp}'),
            html.Li(f'Letzter Wert: {last_timestamp}'),
            html.Li(f'Verfügbarkeit in diesem Zeitraum: {mean_availability * 100:.2f} %')
        ])
    ])
    
    return fig, stats

@callback(
    Output('url', 'search'),
    [Input('hours-dropdown', 'value')],
    [dash.State('ci-store', 'data')],
    prevent_initial_call=True
)
def update_url(hours, ci):
    """Update URL with selected time range"""
    if hours and ci:
        return f'?ci={ci}&hours={hours}'
    elif ci:
        return f'?ci={ci}'
    return ''