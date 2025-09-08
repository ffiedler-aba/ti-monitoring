import dash
from dash import html, dcc, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from mylibrary import *
import yaml
import os
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

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

def load_ci_mttr_mtbf(ci):
    """Load MTTR and MTBF values for a specific CI from statistics.json"""
    try:
        import json
        import os

        stats_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'statistics.json')
        if not os.path.exists(stats_file):
            return 0, 0, 0

        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)

        if ci in stats:
            mttr = stats[ci].get('mttr', 0)
            mtbf = stats[ci].get('mtbf', 0)
            incidents = stats[ci].get('incidents', 0)
            return mttr, mtbf, incidents
        else:
            return 0, 0, 0
    except Exception:
        return 0, 0, 0

def calculate_comprehensive_statistics(ci_data, selected_hours, config_file_name, ci):
    """Calculate comprehensive statistics for the selected time period"""
    if ci_data.empty:
        return {
            'selected_period': {
                'duration_hours': selected_hours,
                'data_points': 0,
                'availability_percent': 0.0,
                'start_time': 'N/A',
                'end_time': 'N/A'
            },
            'overall_record': {
                'start_time': 'N/A',
                'end_time': 'N/A',
                'total_duration_days': 0,
                'total_data_points': 0,
                'data_completeness_percent': 0.0
            },
            'downtime_stats': {
                'downtime_points': 0,
                'downtime_percent': 0.0,
                'downtime_duration_minutes': 0,
                'longest_downtime_points': 0,
                'longest_downtime_minutes': 0,
                'uptime_points': 0,
                'uptime_percent': 0.0,
                'uptime_duration_minutes': 0,
                'longest_uptime_points': 0,
                'longest_uptime_minutes': 0,
                'incidents': 0,
                'mttr': 'N/A',
                'mtbf': 'N/A'
            }
        }

    # Convert times to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(ci_data['times']):
        ci_data['times'] = pd.to_datetime(ci_data['times'])

    # Ensure timezone-aware
    if ci_data['times'].dt.tz is None:
        ci_data['times'] = ci_data['times'].dt.tz_localize('Europe/Berlin')
    else:
        ci_data['times'] = ci_data['times'].dt.tz_convert('Europe/Berlin')

    # Calculate cutoff time for selected period
    cutoff = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin')) - pd.Timedelta(hours=selected_hours)

    # Filter data for selected period
    selected_data = ci_data[ci_data['times'] >= cutoff].copy()

    # Selected period statistics
    selected_duration_hours = selected_hours
    selected_data_points = len(selected_data)
    selected_availability = (selected_data['values'].sum() / selected_data_points * 100) if selected_data_points > 0 else 0.0
    selected_start_time = selected_data['times'].min().strftime('%d.%m.%Y %H:%M:%S Uhr') if not selected_data.empty else 'N/A'
    selected_end_time = selected_data['times'].max().strftime('%d.%m.%Y %H:%M:%S Uhr') if not selected_data.empty else 'N/A'

    # Overall record statistics
    overall_start_time = ci_data['times'].min().strftime('%d.%m.%Y %H:%M:%S Uhr')
    overall_end_time = ci_data['times'].max().strftime('%d.%m.%Y %H:%M:%S Uhr')
    overall_duration = (ci_data['times'].max() - ci_data['times'].min()).total_seconds() / 3600 / 24  # days
    overall_data_points = len(ci_data)
    data_completeness = (overall_data_points / (overall_duration * 24 * 12)) * 100  # Assuming 5-minute intervals

    # Downtime statistics for selected period
    downtime_data = selected_data[selected_data['values'] == 0]
    uptime_data = selected_data[selected_data['values'] == 1]

    downtime_points = len(downtime_data)
    downtime_percent = (downtime_points / selected_data_points * 100) if selected_data_points > 0 else 0.0
    downtime_duration_minutes = downtime_points * 5  # Assuming 5-minute intervals

    uptime_points = len(uptime_data)
    uptime_percent = (uptime_points / selected_data_points * 100) if selected_data_points > 0 else 0.0
    uptime_duration_minutes = uptime_points * 5  # Assuming 5-minute intervals

    # Calculate longest downtime and uptime periods
    longest_downtime_points = 0
    longest_uptime_points = 0

    if not selected_data.empty:
        # Group consecutive values
        selected_data_sorted = selected_data.sort_values('times')
        selected_data_sorted['group'] = (selected_data_sorted['values'] != selected_data_sorted['values'].shift()).cumsum()

        for group_id, group in selected_data_sorted.groupby('group'):
            if group['values'].iloc[0] == 0:  # Downtime group
                longest_downtime_points = max(longest_downtime_points, len(group))
            else:  # Uptime group
                longest_uptime_points = max(longest_uptime_points, len(group))

    longest_downtime_minutes = longest_downtime_points * 5
    longest_uptime_minutes = longest_uptime_points * 5

    # Load MTTR and MTBF from statistics file
    mttr, mtbf, incidents = load_ci_mttr_mtbf(ci)
    mttr_display = f"{mttr:.1f} Min" if mttr > 0 else "N/A"
    mtbf_display = f"{mtbf:.1f} Std" if mtbf > 0 else "N/A"

    return {
        'selected_period': {
            'duration_hours': selected_duration_hours,
            'data_points': selected_data_points,
            'availability_percent': selected_availability,
            'start_time': selected_start_time,
            'end_time': selected_end_time
        },
        'overall_record': {
            'start_time': overall_start_time,
            'end_time': overall_end_time,
            'total_duration_days': overall_duration,
            'total_data_points': overall_data_points,
            'data_completeness_percent': data_completeness
        },
        'downtime_stats': {
            'downtime_points': downtime_points,
            'downtime_percent': downtime_percent,
            'downtime_duration_minutes': downtime_duration_minutes,
            'longest_downtime_points': longest_downtime_points,
            'longest_downtime_minutes': longest_downtime_minutes,
            'uptime_points': uptime_points,
            'uptime_percent': uptime_percent,
            'uptime_duration_minutes': uptime_duration_minutes,
            'longest_uptime_points': longest_uptime_points,
            'longest_uptime_minutes': longest_uptime_minutes,
            'incidents': incidents,
            'mttr': mttr_display,
            'mtbf': mtbf_display
        }
    }

dash.register_page(__name__, path='/plot')

def serve_layout(ci=None):
    """Serve the plot page layout"""
    # Get CI from URL parameters if not provided
    if ci is None:
        from flask import request

        # Get CI from URL parameters
        ci = request.args.get('ci', '')

    if not ci:
        return html.Div([
            html.H1("Fehler: Keine CI angegeben"),
            html.P("Bitte geben Sie eine gültige CI in der URL an (z.B. /plot?ci=CI-0000001)"),
            html.A("Zurück zur Hauptseite", href="/", className="btn btn-primary")
        ])

    # Get CI information
    # For TimescaleDB mode, we need to pass None as file_name
    ci_info = get_data_of_ci(None, ci)

    if ci_info is None or ci_info.empty:
        return html.Div([
            html.H1("Komponente nicht gefunden"),
            html.P(f"Die Komponente {ci} wurde nicht in der Datenbank gefunden."),
            html.A("Zurück zur Hauptseite", href="/", className="btn btn-primary")
        ])

    # Extract CI details
    ci_name = ci_info.iloc[0]['name'] if 'name' in ci_info.columns else ci
    ci_organization = ci_info.iloc[0]['organization'] if 'organization' in ci_info.columns else 'Unbekannt'
    ci_product = ci_info.iloc[0]['product'] if 'product' in ci_info.columns else 'Unbekannt'

    # Load core configuration for default hours
    core_config = load_core_config()
    default_hours = core_config.get('default_hours', 48)

    # Create layout
    layout = html.Div([
        # Main content container
        html.Div(className='main-content', children=[
            # Page title and CI information
            html.Div(className='page-header', children=[
                html.H1(f"Verfügbarkeit der Komponente {ci}"),
                html.P(f"{ci_name}, {ci_organization}, {ci_product}"),
                html.A("Zurück", href="/", className="btn btn-secondary")
            ]),

            # Plot container
            html.Div(className='plot-container', children=[
                dcc.Graph(
                    id='availability-plot',
                    config={'displayModeBar': True, 'displaylogo': False}
                )
            ]),

            # Time selection controls
            html.Div(className='time-selection', children=[
                html.H3("Zeitraum auswählen"),
                html.Div(className='time-controls', children=[
                    html.Label("Darstellungszeitraum (Stunden):"),
                    dcc.Input(
                        id='hours-input',
                        type='number',
                        value=default_hours,
                        min=1,
                        max=168,  # 1 week
                        step=1,
                        className='hours-input'
                    ),
                    html.Button("Aktualisieren", id='update-button', className='btn btn-primary')
                ]),
                html.P("Der Standardwert von 48 Stunden kann über die config.yaml angepasst werden.", className='help-text')
            ]),

            # Comprehensive statistics
            html.Div(id='comprehensive-statistics', className='comprehensive-stats')
        ]),

        # Store for current CI and hours
        dcc.Store(id='ci-store', data=ci),
        dcc.Store(id='hours-store', data=default_hours),

        # Location component for URL updates
        dcc.Location(id='url', refresh=False)
    ])

    return layout

# Set the layout for Dash
layout = serve_layout

@callback(
    [Output('availability-plot', 'figure'),
     Output('comprehensive-statistics', 'children')],
    [Input('update-button', 'n_clicks'),
     Input('hours-input', 'value')],
    [dash.State('ci-store', 'data')],
    prevent_initial_call=False
)
def update_plot_and_stats(n_clicks, selected_hours, ci):
    """Update plot and comprehensive statistics based on selected time range"""
    # Handle case where ci might be None
    if ci is None:
        ci = "Unbekannt"

    # Handle case where selected_hours might be None
    if selected_hours is None:
        selected_hours = 48

    # Simple test plot first
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[1, 2, 3, 4],
        y=[1, 1, 0, 1],
        mode='lines+markers',
        name='Test Verfügbarkeit',
        line=dict(color='green', width=2)
    ))
    fig.update_layout(
        title=f'Test Plot für CI {ci}',
        xaxis_title="Zeit",
        yaxis_title="Verfügbarkeit",
        yaxis=dict(range=[-0.1, 1.1], tickvals=[0, 1], ticktext=['0', '1'])
    )

    # Simple test statistics
    stats_display = html.Div([
        html.H3('Test Statistik'),
        html.P(f'CI: {ci}'),
        html.P(f'Stunden: {selected_hours}'),
        html.P('Dies ist ein Test der Plot-Seite.')
    ])

    return fig, stats_display

@callback(
    Output('url', 'search'),
    [Input('hours-input', 'value')],
    [dash.State('ci-store', 'data')],
    prevent_initial_call=True
)
def update_url(hours, ci):
    """Update URL when hours change"""
    if hours and ci:
        return f"?ci={ci}&hours={hours}"
    elif ci:
        return f"?ci={ci}"
    else:
        return ""
