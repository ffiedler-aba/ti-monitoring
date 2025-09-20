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

def generate_synthetic_availability(hours: int = 24, timezone: str = 'Europe/Berlin'):
    """Generate synthetic availability data with clear outage segments for demo/testing.

    - 5‑Minutentakt
    - enthält 2 Ausfälle (je ~30–45 Minuten), sodass Linien sichtbar unterbrochen werden
    """
    try:
        hours = int(max(1, hours))
    except Exception:
        hours = 24

    now_ts = pd.Timestamp.now(tz=pytz.timezone(timezone)).floor('min')
    start_ts = now_ts - pd.Timedelta(hours=hours)
    idx = pd.date_range(start=start_ts, end=now_ts, freq='5min', tz=pytz.timezone(timezone))

    values = np.ones(len(idx), dtype=int)
    if len(idx) > 30:
        # erster Ausfall: mittig
        mid = len(idx) // 2
        values[max(0, mid - 6): min(len(values), mid + 6)] = 0  # ~60 Minuten
    if len(idx) > 80:
        # zweiter Ausfall: im ersten Drittel
        third = len(idx) // 3
        values[max(0, third - 4): min(len(values), third + 5)] = 0  # ~45 Minuten

    return pd.DataFrame({'times': idx, 'values': values})

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
    # Canonical & JSON-LD
    base = request.url_root.rstrip('/')
    canonical = f"{base}/ci/{ci}" if ci else f"{base}/plot"
    # dynamic OG image with optional CI badge
    from urllib.parse import quote
    q_title = quote('TI-Stats')
    q_subtitle = quote('Verfügbarkeit und Statistiken')
    og_image = f"{base}/og-image.png?title={q_title}&subtitle={q_subtitle}"
    if ci:
        og_image += f"&ci={quote(ci)}"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "url": canonical,
        "name": f"TI-Stats – Verfügbarkeit {ci}" if ci else "TI-Stats – Verfügbarkeit",
        "inLanguage": "de",
        "isPartOf": {"@type": "WebSite", "url": base, "name": "TI-Stats"}
    }

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
        html.Link(rel='canonical', href=canonical),
        html.Meta(property='og:url', content=canonical),
        html.Meta(property='og:image', content=og_image),
        html.Meta(name='twitter:image', content=og_image),
        html.Script(type='application/ld+json', children=[json.dumps(jsonld)]),
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
                html.H3(children=[
                    "Zeitraum auswählen",
                    html.I(className='material-icons', children='info', style={'marginLeft': '8px', 'fontSize': '16px', 'verticalAlign': 'middle'}, title='Wählen Sie einen Zeitraum. Kürzere Zeiträume laden schneller, längere zeigen Trends.')
                ]),
                html.Div(className='time-controls', children=[
                    html.Label(children=[
                        "Darstellungszeitraum:",
                        html.I(className='material-icons', children='info', style={'marginLeft': '6px', 'fontSize': '16px', 'verticalAlign': 'middle'}, title='Bestimmt, wie viele Stunden rückwirkend angezeigt werden.')
                    ]),
                    html.Div(title='Auswahl des rückwirkenden Zeitfensters (z. B. 24h, 48h, 1 Woche).', children=dcc.Dropdown(
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
                    )),
                    html.Button("Aktualisieren", id='update-button', className='btn btn-primary', title='Aktualisiert den Plot basierend auf Ihrer Auswahl (ohne URL-Änderung).')
                ]),
                html.Div(className='trend-controls', children=[
                    html.Label(children=[
                        "Trends:",
                        html.I(
                            className='material-icons',
                            children='info',
                            style={'marginLeft': '6px', 'fontSize': '16px', 'verticalAlign': 'middle'},
                            title='EMA (Exponentieller gleitender Durchschnitt / Exponential Moving Average) glättet die Verfügbarkeit (24h/7d). Incident‑Marker zeigen Statuswechsel (Ausfall/Recovery).'
                        )
                    ]),
                    dcc.Checklist(
                        id='trend-options',
                        options=[
                            {'label': 'EMA 24h', 'value': 'ema24'},
                            {'label': 'EMA 7d', 'value': 'ema168'},
                            {'label': 'Incident-Marker', 'value': 'incidents'}
                        ],
                        value=['ema24'],
                        labelStyle={'display': 'inline-block', 'marginRight': '12px'}
                    )
                ], style={'marginTop': '8px'}),
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
     Input('hours-input', 'value'),
     Input('trend-options', 'value'),
     Input('availability-plot', 'relayoutData')],
    [dash.State('url', 'search'),
     dash.State('ci-store', 'data')],
    prevent_initial_call=False
)
def handle_plot_updates(pathname, n_clicks, hours, trend_options, relayout_data, url_search, ci):
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

    # Determine selected interval/hours
    selected_hours = 48  # fallback
    selected_range = None  # (start_ts, end_ts) if user zoomed/panned

    # Priority 1: react to explicit plot range (zoom/pan)
    try:
        if relayout_data and isinstance(relayout_data, dict):
            # Handle explicit x range from Plotly
            x0 = relayout_data.get('xaxis.range[0]')
            x1 = relayout_data.get('xaxis.range[1]')
            if x0 and x1:
                start_ts = pd.to_datetime(x0)
                end_ts = pd.to_datetime(x1)
                # Normalize timezone to Europe/Berlin
                if start_ts.tzinfo is None:
                    start_ts = start_ts.tz_localize('Europe/Berlin')
                else:
                    start_ts = start_ts.tz_convert('Europe/Berlin')
                if end_ts.tzinfo is None:
                    end_ts = end_ts.tz_localize('Europe/Berlin')
                else:
                    end_ts = end_ts.tz_convert('Europe/Berlin')
                if end_ts > start_ts:
                    selected_range = (start_ts, end_ts)
                    selected_hours = max(1, int((end_ts - start_ts).total_seconds() // 3600))
            # Reset to autorange -> fall back to dropdown/URL
    except Exception:
        selected_range = None

    # Priority 2: hours from dropdown input
    if selected_range is None and hours is not None:
        selected_hours = hours

    # Priority 3: hours from URL
    if selected_range is None and hours is None and url_search:
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
        # Parse demo flag once and reuse
        demo_mode = False
        try:
            if url_search:
                import urllib.parse
                params = urllib.parse.parse_qs(url_search.lstrip('?'))
                demo_mode = params.get('demo', ['0'])[0] in ['1', 'true', 'True']
        except Exception:
            demo_mode = False

        # If demo mode is requested, generate synthetic data regardless of DB
        if demo_mode:
            ci_data = generate_synthetic_availability(hours=selected_hours)
        else:
            ci_data = get_availability_data_of_ci(None, ci)

        if ci_data.empty:
            # Fallback auf synthetische Testdaten, wenn gewünscht (per URL-Flag demo=1)
            try:
                if demo_mode:
                    ci_data = generate_synthetic_availability(hours=selected_hours)
                else:
                    raise ValueError('no_data')
            except Exception:
                pass

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
                html.P('Für diese Komponente sind keine Verfügbarkeitsdaten vorhanden.'),
                html.P('Tipp: Fügen Sie der URL "&demo=1" hinzu, um Testdaten mit Ausfällen anzuzeigen.')
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

        # Calculate and apply selected time window
        if selected_range is not None:
            start_ts, end_ts = selected_range
            selected_data = ci_data[(ci_data['times'] >= start_ts) & (ci_data['times'] <= end_ts)].copy()
        else:
            cutoff = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin')) - pd.Timedelta(hours=selected_hours)
            selected_data = ci_data[ci_data['times'] >= cutoff].copy()

        if selected_data.empty:
            # Try demo mode within selected window
            try:
                demo_mode = False
                if url_search:
                    import urllib.parse
                    params = urllib.parse.parse_qs(url_search.lstrip('?'))
                    demo_mode = params.get('demo', ['0'])[0] in ['1', 'true', 'True']
                if demo_mode:
                    selected_data = generate_synthetic_availability(hours=selected_hours)
            except Exception:
                pass

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
                html.P('Im ausgewählten Zeitraum sind keine Daten verfügbar.'),
                html.P('Tipp: Fügen Sie der URL "&demo=1" hinzu, um Testdaten mit Ausfällen anzuzeigen.')
            ])

            return fig, stats_display, ci_meta_text

        # Create plot with color coding: Red for availability 0, Green for availability 1
        # IMPORTANT: Do not connect green line across downtime. We achieve this by
        # masking opposite values to NaN so Plotly breaks the line between segments.
        fig = go.Figure()

        selected_data_sorted = selected_data.sort_values('times').copy()

        # Build masked series so that lines break across gaps (None/NaN)
        # Use a small epsilon for unavailable to avoid clipping at y=0 baseline
        eps = 0.05
        vals = selected_data_sorted['values'].astype(float).tolist()
        avail_y = [1.0 if v == 1.0 else None for v in vals]
        unavail_y = [eps if v == 0.0 else None for v in vals]

        # Available (green) – gaps over downtime
        fig.add_trace(go.Scatter(
            x=selected_data_sorted['times'],
            y=avail_y,
            mode='lines+markers',
            name='Verfügbar',
            line=dict(color='#10b981', width=3),
            marker=dict(color='#10b981', size=6),
            connectgaps=False,
            hovertemplate='<b>Verfügbar</b><br>Zeit: %{x}<br>Status: %{y}<extra></extra>'
        ))

        # Unavailable (red) – gaps over uptime
        fig.add_trace(go.Scatter(
            x=selected_data_sorted['times'],
            y=unavail_y,
            mode='lines+markers',
            name='Nicht verfügbar',
            line=dict(color='#ef4444', width=4, shape='hv'),
            marker=dict(color='#ef4444', size=6, symbol='square'),
            connectgaps=False,
            hovertemplate='<b>Nicht verfügbar</b><br>Zeit: %{x}<br>Status: %{y}<extra></extra>'
        ))

        # Update layout
        fig.update_layout(
            title=f'Verfügbarkeit der Komponente {ci}',
            xaxis_title="Zeit",
            yaxis_title="Verfügbarkeit",
            yaxis=dict(
                range=[-0.2, 1.1],
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

        # --- Trend Overlays ---
        try:
            trend_options = trend_options or ['ema24']
            selected_data_sorted = selected_data.sort_values('times').copy()
            # Ensure numeric values
            selected_data_sorted['values'] = selected_data_sorted['values'].astype(float)

            # EMA helper (window points based on 5-min cadence)
            points_per_hour = 12
            if 'ema24' in trend_options:
                span_24h = int(24 * points_per_hour)
                if span_24h > 1:
                    ema24 = selected_data_sorted['values'].ewm(span=span_24h, adjust=False, min_periods=max(5, span_24h // 10)).mean()
                    fig.add_trace(go.Scatter(
                        x=selected_data_sorted['times'],
                        y=ema24,
                        mode='lines',
                        name='EMA 24h',
                        line=dict(color='#60a5fa', width=2, dash='solid'),
                        hovertemplate='<b>EMA 24h</b><br>Zeit: %{x}<br>Wert: %{y:.3f}<extra></extra>'
                    ))

            if 'ema168' in trend_options:
                span_7d = int(7 * 24 * points_per_hour)
                if span_7d > 1:
                    ema7d = selected_data_sorted['values'].ewm(span=span_7d, adjust=False, min_periods=max(5, span_7d // 20)).mean()
                    fig.add_trace(go.Scatter(
                        x=selected_data_sorted['times'],
                        y=ema7d,
                        mode='lines',
                        name='EMA 7d',
                        line=dict(color='#3b82f6', width=2, dash='dot'),
                        hovertemplate='<b>EMA 7d</b><br>Zeit: %{x}<br>Wert: %{y:.3f}<extra></extra>'
                    ))

            # Incident/Recovery markers
            if 'incidents' in trend_options:
                selected_data_sorted['prev'] = selected_data_sorted['values'].shift(1)
                incident_mask = (selected_data_sorted['prev'] == 1.0) & (selected_data_sorted['values'] == 0.0)
                recovery_mask = (selected_data_sorted['prev'] == 0.0) & (selected_data_sorted['values'] == 1.0)

                incident_times = selected_data_sorted.loc[incident_mask, 'times']
                recovery_times = selected_data_sorted.loc[recovery_mask, 'times']

                if not incident_times.empty:
                    fig.add_trace(go.Scatter(
                        x=incident_times,
                        y=[0.0] * len(incident_times),
                        mode='markers',
                        name='Incident Start',
                        marker=dict(color='#ef4444', symbol='triangle-down', size=10),
                        hovertemplate='<b>Incident-Start</b><br>Zeit: %{x}<extra></extra>'
                    ))
                if not recovery_times.empty:
                    fig.add_trace(go.Scatter(
                        x=recovery_times,
                        y=[1.0] * len(recovery_times),
                        mode='markers',
                        name='Recovery',
                        marker=dict(color='#10b981', symbol='triangle-up', size=10),
                        hovertemplate='<b>Recovery</b><br>Zeit: %{x}<extra></extra>'
                    ))
        except Exception:
            # Trends sind optional; Fehler hier sollen den Basisplot nicht verhindern
            pass

        # Calculate comprehensive statistics
        stats = calculate_comprehensive_statistics(ci_data, selected_hours, None, ci)

        # Base statistics display
        base_stats_display = create_comprehensive_statistics_display(stats, ci)

        # Additional analytics blocks (SLA, prior-period compare, heatmap)
        extra_blocks = []

        # SLA indicator and prior period comparison
        try:
            try:
                core_cfg = load_core_config()
                sla_target = float(core_cfg.get('sla_target', 99.9))
            except Exception:
                sla_target = 99.9

            # Determine current window
            if 'times' in selected_data.columns and not selected_data.empty:
                window_start = selected_data['times'].min()
                window_end = selected_data['times'].max()
            else:
                window_end = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin'))
                window_start = window_end - pd.Timedelta(hours=selected_hours)

            # Current availability
            cur_points = int(len(selected_data))
            cur_avail_percent = float((selected_data['values'].sum() / cur_points * 100) if cur_points > 0 else 0.0)
            sla_met = cur_avail_percent >= sla_target

            # Prior period window (same duration directly before)
            prior_duration = window_end - window_start
            prior_start = window_start - prior_duration
            prior_end = window_start
            prior_data = ci_data[(ci_data['times'] >= prior_start) & (ci_data['times'] <= prior_end)].copy()
            prior_points = int(len(prior_data))
            prior_avail_percent = float((prior_data['values'].sum() / prior_points * 100) if prior_points > 0 else 0.0)
            delta_pp = (cur_avail_percent - prior_avail_percent) if prior_points > 0 else None

            # SLA block
            extra_blocks.append(
                html.Div([
                    html.H4('SLA', style={'color': '#34495e', 'marginBottom': '15px'}),
                    html.Div([
                        html.Div([
                            html.Strong('Ziel (SLA): '),
                            html.Span(f"{sla_target:.3f}%")
                        ], style={'marginBottom': '8px'}),
                        html.Div([
                            html.Strong('Aktuell: '),
                            html.Span(f"{cur_avail_percent:.3f}%", style={'color': '#10b981' if sla_met else '#ef4444'})
                        ], style={'marginBottom': '8px'}),
                        html.Div([
                            html.Strong('Status: '),
                            html.Span('erreicht' if sla_met else 'nicht erreicht', style={'color': '#10b981' if sla_met else '#ef4444', 'fontWeight': 600})
                        ])
                    ], style={'paddingLeft': '20px'})
                ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'})
            )

            # Prior-period comparison block
            prior_text = f"{prior_avail_percent:.3f}%" if prior_points > 0 else 'N/A'
            delta_text = (f"{delta_pp:+.3f} pp" if delta_pp is not None else 'N/A')
            delta_color = '#10b981' if (delta_pp is not None and delta_pp >= 0) else '#ef4444'
            extra_blocks.append(
                html.Div([
                    html.H4('Vergleich zur Vorperiode', style={'color': '#34495e', 'marginBottom': '15px'}),
                    html.Div([
                        html.Div([
                            html.Strong('Vorperiode (gleiche Dauer): '),
                            html.Span(prior_text)
                        ], style={'marginBottom': '8px'}),
                        html.Div([
                            html.Strong('Differenz: '),
                            html.Span(delta_text, style={'color': delta_color})
                        ], style={'marginBottom': '8px'})
                    ], style={'paddingLeft': '20px'})
                ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'})
            )
        except Exception:
            pass

        # Incident heatmap (weekday × hour) within current window
        try:
            selected_data_sorted = selected_data.sort_values('times').copy()
            selected_data_sorted['prev'] = selected_data_sorted['values'].shift(1)
            incident_mask = (selected_data_sorted['prev'] == 1) & (selected_data_sorted['values'] == 0)
            incident_times = selected_data_sorted.loc[incident_mask, 'times']
            if not incident_times.empty:
                weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
                hours = list(range(24))
                matrix = [[0 for _ in hours] for _ in weekdays]
                for ts in incident_times:
                    try:
                        wd = int(ts.weekday())  # 0=Mon
                        hr = int(ts.hour)
                        matrix[wd][hr] += 1
                    except Exception:
                        continue
                heatmap_fig = go.Figure(data=go.Heatmap(z=matrix, x=hours, y=weekdays, colorscale='Reds', colorbar=dict(title='Incidents')))
                heatmap_fig.update_layout(title='Incident-Heatmap (Wochentag × Stunde)', xaxis_title='Stunde', yaxis_title='Wochentag', margin=dict(l=50, r=30, t=50, b=50))
                extra_blocks.append(
                    html.Div([
                        html.H4('Incident-Heatmap', style={'color': '#34495e', 'marginBottom': '10px'}),
                        dcc.Graph(id='incident-heatmap', figure=heatmap_fig, config={'displaylogo': False})
                    ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'})
                )
        except Exception:
            pass

        # Compose final statistics display
        stats_display = html.Div([base_stats_display, *extra_blocks])

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
