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

def format_duration(hours):
    """Format duration in a human-readable way"""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} Minuten"
    elif hours < 24:
        return f"{hours:.1f} Stunden"
    else:
        days = hours / 24
        return f"{days:.1f} Tage"

def calculate_comprehensive_statistics(ci_data, selected_hours, config_file_name, ci):
    """
    Calculate comprehensive statistics for a CI including:
    - Time range statistics (beginning/end of recording)
    - Data point counts
    - Downtime statistics (time and percentage)
    - Additional useful metrics
    """
    if ci_data.empty:
        return {}
    
    # Get all available data (not just the selected time range)
    all_data = get_availability_data_of_ci(config_file_name, ci)
    
    # Basic statistics for selected time range
    selected_data = ci_data
    number_of_values = len(selected_data['values'])
    mean_availability = np.mean(selected_data['values'].values)
    first_timestamp_selected = selected_data['times'].iloc[0]
    last_timestamp_selected = selected_data['times'].iloc[-1]
    
    # Statistics for entire available data
    total_records = len(all_data['values'])
    first_timestamp_total = all_data['times'].iloc[0]
    last_timestamp_total = all_data['times'].iloc[-1]
    
    # Calculate downtime statistics for selected time range
    downtime_count = (selected_data['values'] == 0).sum()
    uptime_count = (selected_data['values'] == 1).sum()
    downtime_percentage = (downtime_count / number_of_values) * 100 if number_of_values > 0 else 0
    uptime_percentage = (uptime_count / number_of_values) * 100 if number_of_values > 0 else 0
    
    # Calculate total downtime duration (assuming 5-minute intervals)
    downtime_minutes = downtime_count * 5
    downtime_hours = downtime_minutes / 60
    downtime_days = downtime_hours / 24
    
    # Calculate total uptime duration
    uptime_minutes = uptime_count * 5
    uptime_hours = uptime_minutes / 60
    uptime_days = uptime_hours / 24
    
    # Calculate total recording duration
    total_duration = (last_timestamp_total - first_timestamp_total).total_seconds() / 3600  # hours
    total_duration_days = total_duration / 24
    
    # Calculate expected data points (every 5 minutes)
    expected_points = int(total_duration * 12)  # 12 points per hour
    data_completeness = (total_records / expected_points) * 100 if expected_points > 0 else 0
    
    # Calculate longest consecutive downtime and uptime periods
    def find_longest_consecutive(data, value):
        max_consecutive = 0
        current_consecutive = 0
        for val in data:
            if val == value:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        return max_consecutive
    
    longest_downtime_consecutive = find_longest_consecutive(selected_data['values'], 0)
    longest_uptime_consecutive = find_longest_consecutive(selected_data['values'], 1)
    
    # Convert consecutive periods to time
    longest_downtime_hours = longest_downtime_consecutive * 5 / 60
    longest_uptime_hours = longest_uptime_consecutive * 5 / 60
    
    return {
        # Selected time range statistics
        'selected_hours': selected_hours,
        'number_of_values': number_of_values,
        'mean_availability': mean_availability,
        'first_timestamp_selected': first_timestamp_selected,
        'last_timestamp_selected': last_timestamp_selected,
        
        # Total recording statistics
        'total_records': total_records,
        'first_timestamp_total': first_timestamp_total,
        'last_timestamp_total': last_timestamp_total,
        'total_duration_hours': total_duration,
        'total_duration_days': total_duration_days,
        'data_completeness': data_completeness,
        
        # Downtime statistics
        'downtime_count': downtime_count,
        'uptime_count': uptime_count,
        'downtime_percentage': downtime_percentage,
        'uptime_percentage': uptime_percentage,
        'downtime_minutes': downtime_minutes,
        'downtime_hours': downtime_hours,
        'downtime_days': downtime_days,
        'uptime_minutes': uptime_minutes,
        'uptime_hours': uptime_hours,
        'uptime_days': uptime_days,
        
        # Consecutive periods
        'longest_downtime_consecutive': longest_downtime_consecutive,
        'longest_uptime_consecutive': longest_uptime_consecutive,
        'longest_downtime_hours': longest_downtime_hours,
        'longest_uptime_hours': longest_uptime_hours
    }

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
        
        # Plot section (moved up to avoid overlay issues)
        html.Div(id='plot-container', children=[
            dcc.Graph(id='availability-plot')
        ]),
        
        # Time range selector (moved below plot)
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
                    style={
                        'width': '200px', 
                        'display': 'inline-block', 
                        'margin-left': '10px',
                        'position': 'relative',
                        'z-index': '9999'
                    }
                ),
                html.Button('Aktualisieren', id='update-button', className='button', style={'margin-left': '10px'})
            ]),
            html.P('Der Standardwert von ' + str(config_stats_delta_hours) + ' Stunden kann über die config.yaml angepasst werden.', 
                   style={'font-size': '0.9rem', 'color': 'var(--gray-600)', 'margin-top': 'var(--spacing-sm)'})
        ]),
        
        # Comprehensive Statistics section (now below the plot)
        html.Div(id='comprehensive-statistics', className='box'),
        
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
     Output('comprehensive-statistics', 'children')],
    [Input('update-button', 'n_clicks'),
     Input('hours-dropdown', 'value')],
    [dash.State('ci-store', 'data')],
    prevent_initial_call=False
)
def update_plot_and_stats(n_clicks, selected_hours, ci):
    """Update plot and comprehensive statistics based on selected time range"""
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
    
    # Calculate comprehensive statistics
    stats = calculate_comprehensive_statistics(ci_data, selected_hours, config_file_name, ci)
    
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
    
    # Create comprehensive statistics display
    stats_display = html.Div(className='comprehensive-stats', children=[
        html.H3('📊 Umfassende Statistik'),
        
        # Selected time range statistics
        html.Div(className='stats-section', children=[
            html.H4('🎯 Ausgewählter Zeitraum'),
            html.Div(className='stats-grid', children=[
                html.Div(className='stat-item', children=[
                    html.Strong('Zeitraum: '),
                    html.Span(f'{selected_hours} Stunden')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Anzahl Datensätze: '),
                    html.Span(f'{stats["number_of_values"]:,}')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Verfügbarkeit: '),
                    html.Span(f'{stats["mean_availability"] * 100:.2f}%')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Von: '),
                    html.Span(stats["first_timestamp_selected"].strftime('%d.%m.%Y %H:%M:%S Uhr'))
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Bis: '),
                    html.Span(stats["last_timestamp_selected"].strftime('%d.%m.%Y %H:%M:%S Uhr'))
                ])
            ])
        ]),
        
        # Total recording statistics
        html.Div(className='stats-section', children=[
            html.H4('📅 Gesamte Aufzeichnung'),
            html.Div(className='stats-grid', children=[
                html.Div(className='stat-item', children=[
                    html.Strong('Beginn der Aufzeichnung: '),
                    html.Span(stats["first_timestamp_total"].strftime('%d.%m.%Y %H:%M:%S Uhr'))
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Ende der Aufzeichnung: '),
                    html.Span(stats["last_timestamp_total"].strftime('%d.%m.%Y %H:%M:%S Uhr'))
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Gesamtdauer: '),
                    html.Span(f'{format_duration(stats["total_duration_hours"])}')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Gesamte Datensätze: '),
                    html.Span(f'{stats["total_records"]:,}')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Datenvollständigkeit: '),
                    html.Span(f'{stats["data_completeness"]:.1f}%')
                ])
            ])
        ]),
        
        # Downtime statistics
        html.Div(className='stats-section', children=[
            html.H4('🔴 Downtime-Statistik (ausgewählter Zeitraum)'),
            html.Div(className='stats-grid', children=[
                html.Div(className='stat-item', children=[
                    html.Strong('Downtime: '),
                    html.Span(f'{stats["downtime_count"]:,} Datensätze ({stats["downtime_percentage"]:.1f}%)')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Downtime-Dauer: '),
                    html.Span(f'{format_duration(stats["downtime_hours"])}')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Längste Downtime: '),
                    html.Span(f'{stats["longest_downtime_consecutive"]} Messungen ({format_duration(stats["longest_downtime_hours"])})')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Uptime: '),
                    html.Span(f'{stats["uptime_count"]:,} Datensätze ({stats["uptime_percentage"]:.1f}%)')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Uptime-Dauer: '),
                    html.Span(f'{format_duration(stats["uptime_hours"])}')
                ]),
                html.Div(className='stat-item', children=[
                    html.Strong('Längste Uptime: '),
                    html.Span(f'{stats["longest_uptime_consecutive"]} Messungen ({format_duration(stats["longest_uptime_hours"])})')
                ])
            ])
        ])
    ])
    
    return fig, stats_display

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