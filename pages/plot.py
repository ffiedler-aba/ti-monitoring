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

dash.register_page(__name__, path='/plot')

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

def create_comprehensive_statistics_display(stats, ci):
    """Create comprehensive statistics display for the plot page"""
    selected_period = stats['selected_period']
    overall_record = stats['overall_record']
    downtime_stats = stats['downtime_stats']
    
    return html.Div([
        html.H3('Detaillierte Statistiken', style={'color': '#2c3e50', 'marginBottom': '20px'}),
        
        # Selected Period Statistics
        html.Div([
            html.H4('Ausgewählter Zeitraum', style={'color': '#34495e', 'marginBottom': '15px'}),
            html.Div([
                html.Div([
                    html.Strong('Dauer: '),
                    html.Span(f"{selected_period['duration_hours']} Stunden")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Datenpunkte: '),
                    html.Span(f"{selected_period['data_points']}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Verfügbarkeit: '),
                    html.Span(f"{selected_period['availability_percent']:.2f}%", 
                             style={'color': '#10b981' if selected_period['availability_percent'] >= 99 else '#ef4444'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Zeitraum: '),
                    html.Span(f"{selected_period['start_time']} - {selected_period['end_time']}")
                ], style={'marginBottom': '8px'})
            ], style={'paddingLeft': '20px'})
        ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'}),
        
        # Downtime Statistics
        html.Div([
            html.H4('Ausfallstatistiken', style={'color': '#34495e', 'marginBottom': '15px'}),
            html.Div([
                html.Div([
                    html.Strong('Ausfallpunkte: '),
                    html.Span(f"{downtime_stats['downtime_points']}", style={'color': '#ef4444'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Ausfallanteil: '),
                    html.Span(f"{downtime_stats['downtime_percent']:.2f}%", style={'color': '#ef4444'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Ausfalldauer: '),
                    html.Span(f"{format_duration(downtime_stats['downtime_duration_minutes'] / 60)}", style={'color': '#ef4444'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Längster Ausfall: '),
                    html.Span(f"{format_duration(downtime_stats['longest_downtime_minutes'] / 60)}", style={'color': '#ef4444'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Verfügbarkeitspunkte: '),
                    html.Span(f"{downtime_stats['uptime_points']}", style={'color': '#10b981'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Verfügbarkeitsanteil: '),
                    html.Span(f"{downtime_stats['uptime_percent']:.2f}%", style={'color': '#10b981'})
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Längste Verfügbarkeit: '),
                    html.Span(f"{format_duration(downtime_stats['longest_uptime_minutes'] / 60)}", style={'color': '#10b981'})
                ], style={'marginBottom': '8px'})
            ], style={'paddingLeft': '20px'})
        ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'}),
        
        # MTTR/MTBF Statistics
        html.Div([
            html.H4('MTTR/MTBF Statistiken', style={'color': '#34495e', 'marginBottom': '15px'}),
            html.Div([
                html.Div([
                    html.Strong('Anzahl Störungen: '),
                    html.Span(f"{downtime_stats['incidents']}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('MTTR (Mean Time To Repair): '),
                    html.Span(downtime_stats['mttr'])
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('MTBF (Mean Time Between Failures): '),
                    html.Span(downtime_stats['mtbf'])
                ], style={'marginBottom': '8px'})
            ], style={'paddingLeft': '20px'})
        ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'}),
        
        # Overall Record Statistics
        html.Div([
            html.H4('Gesamter Datensatz', style={'color': '#34495e', 'marginBottom': '15px'}),
            html.Div([
                html.Div([
                    html.Strong('Gesamtdauer: '),
                    html.Span(f"{overall_record['total_duration_days']:.1f} Tage")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Gesamte Datenpunkte: '),
                    html.Span(f"{overall_record['total_data_points']}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Datenvollständigkeit: '),
                    html.Span(f"{overall_record['data_completeness_percent']:.2f}%")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Strong('Zeitraum: '),
                    html.Span(f"{overall_record['start_time']} - {overall_record['end_time']}")
                ], style={'marginBottom': '8px'})
            ], style={'paddingLeft': '20px'})
        ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px'})
    ], style={'marginTop': '30px'})

def serve_layout(**kwargs):
    """Serve the plot page layout"""
    # Get CI from URL parameters (kann initial leer sein)
    from flask import request
    ci = request.args.get('ci', '') or ''

    # Get CI information (optional; Seite rendert auch ohne CI)
    # For TimescaleDB mode, we need to pass None as file_name
    ci_info = get_data_of_ci(None, ci) if ci else None

    # Extract CI details mit sicheren Fallbacks
    if ci_info is not None and hasattr(ci_info, 'empty') and not ci_info.empty:
        ci_name = ci_info.iloc[0]['name'] if 'name' in ci_info.columns else ci
        ci_organization = ci_info.iloc[0]['organization'] if 'organization' in ci_info.columns else 'Unbekannt'
        ci_product = ci_info.iloc[0]['product'] if 'product' in ci_info.columns else 'Unbekannt'
    else:
        ci_name = ci if ci else 'Unbekannt'
        ci_organization = 'Unbekannt'
        ci_product = 'Unbekannt'

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
                html.P(id='ci-meta', children=f"{ci_name}, {ci_organization}, {ci_product}"),
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
                    html.Label("Darstellungszeitraum:"),
                    dcc.Dropdown(
                        id='hours-input',
                        options=[
                            {'label': '12 Stunden', 'value': 12},
                            {'label': '24 Stunden (1 Tag)', 'value': 24},
                            {'label': '48 Stunden (2 Tage)', 'value': 48},
                            {'label': '72 Stunden (3 Tage)', 'value': 72},
                            {'label': '1 Woche', 'value': 168},
                            {'label': '2 Wochen', 'value': 336},
                            {'label': '1 Monat', 'value': 720},
                            {'label': '2 Monate', 'value': 1440},
                            {'label': '3 Monate', 'value': 2160}
                        ],
                        value=default_hours,
                        clearable=False,
                        className='hours-dropdown'
                    ),
                    html.Button("Aktualisieren", id='update-button', className='btn btn-primary')
                ]),
                html.P("Wählen Sie einen vordefinierten Zeitraum für die Darstellung der Verfügbarkeitsdaten.", className='help-text')
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

# Set the layout for Dash - this will be called by Dash with the current path
layout = serve_layout

# Consolidated callback - handles both initial load and UI interactions
@callback(
    [Output('availability-plot', 'figure'),
     Output('comprehensive-statistics', 'children'),
     Output('ci-meta', 'children')],
    [Input('url', 'pathname'),
     Input('update-button', 'n_clicks'),
     Input('hours-input', 'value')],
    [dash.State('url', 'search'),
     dash.State('ci-store', 'data')],
    prevent_initial_call=False
)
def handle_plot_updates(pathname, n_clicks, hours, url_search, ci):
    """Handle both initial load and UI interactions for plot updates"""
    # Resolve CI: prefer store, then URL, then request args
    if not ci:
        # Try to parse from URL search
        if url_search:
            import urllib.parse
            params = urllib.parse.parse_qs(url_search.lstrip('?'))
            parsed_ci = params.get('ci', [None])[0]
            if parsed_ci:
                ci = parsed_ci
        # Fallback to request args
        if not ci:
            from flask import request
            ci = request.args.get('ci', 'Unbekannt')
    
    # Determine selected hours based on input priority
    selected_hours = 48  # default
    
    # Priority 1: hours from dropdown input
    if hours is not None:
        selected_hours = hours
    # Priority 2: hours from URL
    elif url_search:
        import urllib.parse
        params = urllib.parse.parse_qs(url_search.lstrip('?'))
        if 'hours' in params:
            try:
                selected_hours = int(params['hours'][0])
            except (ValueError, IndexError):
                selected_hours = 48
    
    # Do not update URL to avoid full page re-render; only update UI
    
    # Prepare CI meta from metadata table
    try:
        ci_info = get_data_of_ci(None, ci) if ci else None
        if ci_info is not None and hasattr(ci_info, 'empty') and not ci_info.empty:
            ci_name = ci_info.iloc[0]['name'] if 'name' in ci_info.columns else ci
            ci_organization = ci_info.iloc[0]['organization'] if 'organization' in ci_info.columns else 'Unbekannt'
            ci_product = ci_info.iloc[0]['product'] if 'product' in ci_info.columns else 'Unbekannt'
        else:
            ci_name = ci if ci else 'Unbekannt'
            ci_organization = 'Unbekannt'
            ci_product = 'Unbekannt'
        ci_meta_text = f"{ci_name}, {ci_organization}, {ci_product}"
    except Exception:
        ci_meta_text = f"{ci if ci else 'Unbekannt'}, Unbekannt, Unbekannt"

    # Load and process data
    try:
        ci_data = get_availability_data_of_ci(None, ci)
        
        if ci_data.empty:
            # No data available
            fig = go.Figure()
            fig.add_annotation(
                text="Keine Daten verfügbar für diese CI",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(
                title=f'Verfügbarkeit der Komponente {ci}',
                xaxis_title="Zeit",
                yaxis_title="Verfügbarkeit",
                yaxis=dict(range=[-0.1, 1.1], tickvals=[0, 1], ticktext=['Nicht verfügbar', 'Verfügbar'])
            )
            
            stats_display = html.Div([
                html.H3('Keine Daten verfügbar'),
                html.P(f'CI: {ci}'),
                html.P(f'Zeitraum: {selected_hours} Stunden'),
                html.P('Für diese Komponente sind keine Verfügbarkeitsdaten vorhanden.')
            ])
            
            return fig, stats_display, ci_meta_text
        
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
        
        if selected_data.empty:
            # No data in selected period
            fig = go.Figure()
            fig.add_annotation(
                text=f"Keine Daten im ausgewählten Zeitraum ({selected_hours} Stunden)",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(
                title=f'Verfügbarkeit der Komponente {ci}',
                xaxis_title="Zeit",
                yaxis_title="Verfügbarkeit",
                yaxis=dict(range=[-0.1, 1.1], tickvals=[0, 1], ticktext=['Nicht verfügbar', 'Verfügbar'])
            )
            
            stats_display = html.Div([
                html.H3('Keine Daten im Zeitraum'),
                html.P(f'CI: {ci}'),
                html.P(f'Zeitraum: {selected_hours} Stunden'),
                html.P('Im ausgewählten Zeitraum sind keine Daten verfügbar.')
            ])
            
            return fig, stats_display, ci_meta_text
        
        # Create plot with color coding: Red for availability 0, Green for availability 1
        fig = go.Figure()
        
        # Separate data points by availability value
        available_data = selected_data[selected_data['values'] == 1]
        unavailable_data = selected_data[selected_data['values'] == 0]
        
        # Add trace for available periods (green)
        if not available_data.empty:
            fig.add_trace(go.Scatter(
                x=available_data['times'],
                y=available_data['values'],
                mode='lines+markers',
                name='Verfügbar',
                line=dict(color='#10b981', width=3),  # Green color
                marker=dict(color='#10b981', size=6),
                hovertemplate='<b>Verfügbar</b><br>Zeit: %{x}<br>Status: %{y}<extra></extra>'
            ))
        
        # Add trace for unavailable periods (red)
        if not unavailable_data.empty:
            fig.add_trace(go.Scatter(
                x=unavailable_data['times'],
                y=unavailable_data['values'],
                mode='lines+markers',
                name='Nicht verfügbar',
                line=dict(color='#ef4444', width=3),  # Red color
                marker=dict(color='#ef4444', size=6),
                hovertemplate='<b>Nicht verfügbar</b><br>Zeit: %{x}<br>Status: %{y}<extra></extra>'
            ))
        
        # Update layout
        fig.update_layout(
            title=f'Verfügbarkeit der Komponente {ci}',
            xaxis_title="Zeit",
            yaxis_title="Verfügbarkeit",
            yaxis=dict(
                range=[-0.1, 1.1], 
                tickvals=[0, 1], 
                ticktext=['Nicht verfügbar', 'Verfügbar'],
                tickfont=dict(size=12)
            ),
            xaxis=dict(
                tickfont=dict(size=10),
                tickangle=45
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=50, t=80, b=80)
        )
        
        # Calculate comprehensive statistics
        stats = calculate_comprehensive_statistics(ci_data, selected_hours, None, ci)
        
        # Create statistics display
        stats_display = create_comprehensive_statistics_display(stats, ci)
        
    except Exception as e:
        # Error handling
        fig = go.Figure()
        fig.add_annotation(
            text=f"Fehler beim Laden der Daten: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color='red')
        )
        fig.update_layout(
            title=f'Fehler - Verfügbarkeit der Komponente {ci}',
            xaxis_title="Zeit",
            yaxis_title="Verfügbarkeit"
        )
        
        stats_display = html.Div([
            html.H3('Fehler beim Laden der Daten'),
            html.P(f'CI: {ci}'),
            html.P(f'Fehler: {str(e)}'),
            html.P('Bitte versuchen Sie es später erneut.')
        ])
    
    return fig, stats_display, ci_meta_text

# Page registration is handled in app.py
