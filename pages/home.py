import dash
from dash import html, dcc, callback, Input, Output, State, clientside_callback
from mylibrary import *
import yaml
import os
import functools
import time
import gc
import pandas as pd
import json

# Configuration cache for home page with size limit
_home_config_cache = {}
_home_config_cache_timestamp = 0
_home_config_cache_ttl = 300  # 5 seconds cache TTL
_home_config_cache_max_size = 10  # Limit cache size

# Lightweight layout cache to avoid recomputing heavy DOM trees frequently
_home_layout_cache = None
_home_layout_cache_ts = 0
_home_layout_cache_ttl = 60  # seconds

# Limit how many items we render per product group to keep DOM small
_max_items_per_group = 50

def load_config():
    """Load configuration from YAML file with caching"""
    global _home_config_cache, _home_config_cache_timestamp

    current_time = time.time()
    if (not _home_config_cache or
        current_time - _home_config_cache_timestamp > _home_config_cache_ttl):

        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                _home_config_cache = yaml.safe_load(f) or {}
            _home_config_cache_timestamp = current_time

            # Limit cache size
            if len(_home_config_cache) > _home_config_cache_max_size:
                # Keep only the most recent entries
                keys = list(_home_config_cache.keys())[:_home_config_cache_max_size]
                _home_config_cache = {k: _home_config_cache[k] for k in keys}
        except (FileNotFoundError, Exception):
            _home_config_cache = {}
            _home_config_cache_timestamp = current_time

    return _home_config_cache

def load_core_config():
    """Load core configuration from cached config"""
    config = load_config()
    return config.get('core', {})

dash.register_page(__name__, path='/')

# No callback needed - table is scrollable

def create_incidents_table(incidents_data, show_all=False):
    """Erstellt eine erweiterbare Tabelle mit den letzten Incidents"""
    if not incidents_data:
        return html.P("Keine Incidents verfügbar.")

    # Show limited incidents by default for performance
    display_incidents = incidents_data if show_all else incidents_data[:10]

    # Create table rows
    table_rows = []
    for incident in display_incidents:
        # Determine status styling
        status_class = 'incident-ongoing' if incident['status'] == 'ongoing' else 'incident-resolved'
        status_text = 'Noch gestört' if incident['status'] == 'ongoing' else 'Wieder aktiv'

        # Format duration
        duration_hours = incident['duration_minutes'] / 60.0
        if duration_hours < 1:
            duration_text = f"{incident['duration_minutes']:.0f} Min"
        else:
            duration_text = f"{duration_hours:.1f} Std"

        # Format timestamps
        start_time = pd.to_datetime(incident['incident_start']).tz_convert('Europe/Berlin').strftime('%d.%m.%Y %H:%M')
        end_time = ''
        if incident['incident_end']:
            end_time = pd.to_datetime(incident['incident_end']).tz_convert('Europe/Berlin').strftime('%d.%m.%Y %H:%M')
        else:
            end_time = 'Laufend'

        table_rows.append(html.Tr([
            html.Td([
                html.A(incident['ci'], href=f'/plot?ci={incident["ci"]}', className='ci-link'),
                html.Br(),
                html.Span(incident['name'], className='ci-name')
            ]),
            html.Td([
                html.Span(incident['organization'], className='org-name'),
                html.Br(),
                html.Span(incident['product'], className='product-name')
            ]),
            html.Td(start_time, className='timestamp'),
            html.Td(end_time, className='timestamp'),
            html.Td(duration_text, className='duration'),
            html.Td([
                html.Span(status_text, className=f'status-badge {status_class}')
            ])
        ]))

    # No expand button needed - table is scrollable

    return html.Div([
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("CI"),
                    html.Th("Organisation"),
                    html.Th("Beginn"),
                    html.Th("Ende"),
                    html.Th("Dauer"),
                    html.Th("Status")
                ])
            ]),
            html.Tbody(table_rows)
        ], className='incidents-table')
    ], className='incidents-table-container')

def create_accordion_element(group_name, group_data):
    """Create accordion element for a group of CIs"""
    # Ensure group_data is a DataFrame and handle it properly
    if hasattr(group_data, 'empty') and group_data.empty:
        return html.Div(className='accordion-element', children=[
            html.Div(className='accordion-element-title', children=[
                html.Span(className='availability-icon unavailable'),
                html.Span(className='group-name', children=f'{group_name} (0/0)'),
                html.Span(className='expand-collapse-icon', children='+')
            ]),
            html.Div(className='accordion-element-content', children=[
                html.P('Keine Daten verfügbar für diese Gruppe.')
            ])
        ])

    # Calculate availability statistics
    current_availability_sum = group_data['current_availability'].sum()
    total_count = len(group_data)
    available_count = (group_data['current_availability'] == 1).sum()

    # Determine availability status
    if current_availability_sum == total_count:
        availability_class = 'available'
    elif current_availability_sum == 0:
        availability_class = 'unavailable'
    else:
        availability_class = 'impaired'

    # Apply per-group item limit
    limited_group_data = group_data.head(_max_items_per_group)

    # Compute remaining count for hint
    remaining = max(0, len(group_data) - len(limited_group_data))

    return html.Div(className='accordion-element', children = [
        html.Div(
            className='accordion-element-title',
            children = [
                html.Span(
                    className=f'availability-icon {availability_class}',
                ),
                html.Span(
                    className = 'group-name',
                    children = f'{group_name} ({available_count}/{total_count})'
                ),
                html.Span(className='expand-collapse-icon', children='+')
            ]
        ),
        html.Div(className='accordion-element-content', children = [
            html.Ul(children = [
                html.Li([
                    html.Span(
                        className='availability-icon ' + (
                            'available' if row['current_availability'] == 1
                            else 'unavailable'
                        )
                    ),
                    html.Div([
                        html.A(str(row['ci']), href='/plot?ci=' + str(row['ci'])),
                        ': ' + row['name'] + ', ' + row['organization'] + ', ' + pretty_timestamp(row['time'])
                    ])
                ]) for _, row in limited_group_data.iterrows()
            ]),
            (html.Div(
                ['… und ', html.Strong(str(remaining)), ' weitere Einträge, siehe ', html.A('Statistiken', href='/stats')]
            ) if remaining > 0 else None)
        ])
    ])



def serve_layout():
    # Return cached layout if fresh
    global _home_layout_cache, _home_layout_cache_ts
    now_ts = time.time()
    if _home_layout_cache is not None and (now_ts - _home_layout_cache_ts) < _home_layout_cache_ttl:
        return _home_layout_cache
    # Load core configurations (now cached)
    core_config = load_core_config()

    # TimescaleDB mode - no file_name needed
    config_file_name = None
    config_url = core_config.get('url')

    # Load incidents data from statistics.json
    incidents_data = []
    try:
        statistics_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'statistics.json')
        if os.path.exists(statistics_file_path):
            with open(statistics_file_path, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                incidents_data = stats.get('recent_incidents', [])
    except Exception as e:
        print(f"Error loading incidents data: {e}")
        incidents_data = []

    # Try to get data from TimescaleDB
    try:
        cis = get_data_of_all_cis_from_timescaledb()
    except Exception as e:
        print(f"Error reading data from TimescaleDB: {e}")
        cis = pd.DataFrame()  # Empty DataFrame

    # Check if DataFrame is empty
    if cis.empty:
        # Try to load data from API if URL is available
        if config_url:
            try:
                print(f"Loading data from API: {config_url}")
                # For TimescaleDB mode, we don't need to call update_file
                # The cron job should handle API updates
                print("API updates are handled by the cron job in TimescaleDB mode")
            except Exception as e:
                print(f"Error loading data from API: {e}")

        # If still empty, show message
        if cis.empty:
            layout = html.Div([
                html.P('Keine Daten verfügbar. Versuche Daten von der API zu laden...'),
                html.P('Falls das Problem weiterhin besteht, überprüfen Sie die API-Verbindung.'),
                html.P(f'API URL: {config_url or "Nicht konfiguriert"}'),
                html.P('Datenbank: TimescaleDB')
            ])
            return layout

    # Check if 'product' column exists
    if 'product' not in cis.columns:
        layout = html.Div([
            html.P('Daten sind verfügbar, aber die Spalte "product" fehlt. Möglicherweise ist die Datenstruktur fehlerhaft.'),
            html.P('Verfügbare Spalten: ' + ', '.join(cis.columns.tolist())),
            html.P(f'Anzahl Datensätze: {len(cis)}')
        ])
        return layout

    # Optimize DataFrame operations
    try:
        grouped = cis.groupby('product')
    except Exception as e:
        layout = html.Div([
            html.P('Fehler beim Gruppieren der Daten nach Produkt.'),
            html.P(f'Fehler: {str(e)}'),
            html.P(f'Verfügbare Spalten: {", ".join(cis.columns.tolist()) if not cis.empty else "Keine"}')
        ])
        return layout



    # Create accordion elements efficiently
    accordion_elements = []
    for group_name, group_data in grouped:
        accordion_elements.append(create_accordion_element(group_name, group_data))

    # Force garbage collection after processing large DataFrames
    gc.collect()

    # Clean up large DataFrames immediately after use
    if 'cis' in locals():
        del cis
    if 'grouped' in locals():
        del grouped
    gc.collect()

    # Create incidents table (show first 5 by default)
    incidents_table = create_incidents_table(incidents_data, show_all=False)

    # Canonical URL & JSON-LD (Organization/WebSite/HomePage)
    from flask import request as _flask_request
    _base = _flask_request.url_root.rstrip('/')
    _canonical = f"{_base}/"
    _og_image = f"{_base}/og-image.png?title=TI-Stats&subtitle=Verf%C3%BCgbarkeit%20und%20Statistiken&hours=24"
    _jsonld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "url": _canonical,
        "name": "TI-Stats – Verfügbarkeit und Statistiken",
        "inLanguage": "de",
        "isPartOf": {"@type": "WebSite", "url": _base, "name": "TI-Stats"}
    }

    layout = html.Div([
        # SEO head helpers
        html.Link(rel='canonical', href=_canonical),
        html.Meta(name='og:url', content=_canonical),
        html.Meta(name='og:image', content=_og_image),
        html.Meta(name='twitter:image', content=_og_image),
        html.Script(type='application/ld+json', children=[json.dumps(_jsonld)]),
        html.P([
            'ti-stats.net basiert auf Lukas Schmidt-Russnaks ',
            html.A('TI-Monitoring', href='https://ti-monitoring.de'),
            '. Die Seite wurde mit Statistiken, Benachrichtigungen etc. von Grund auf erweitert und angepasst. Daten werden alle 5 Minuten aktualisiert und für 6 Monate gespeichert.'
        ]),

        html.P([
            'Du hast auch die Möglichkeit, Benachrichtigungen individuell zu ',
            html.A('abonnieren', href='/notifications'),
            '. Diese werden dir über deinen persönlichen Apprise-Link gesendet, wenn sich der Status einer der abonierten Komponenten ändert.'
        ]),

        # Incidents section
        html.Div([
            html.H3("Letzte Incidents", className='incidents-title'),
            html.Div([
                dcc.Store(id='incidents-data-store', data=incidents_data),
                html.Div(id='incidents-table-container', children=incidents_table)
            ], className='incidents-container')
        ], className='incidents-section'),

        # Alle CIs mit Downtimes (5 sichtbar, scrollbar)
        html.Div([
            html.H3("Alle TI-Komponenten", className='ci-all-title'),
            html.Div(id='ci-all-table-container')
        ], className='ci-all-section', style={
            'maxHeight': '260px',  # ~5 Zeilen sichtbar
            'overflowY': 'auto',
            'border': '1px solid #e9ecef',
            'borderRadius': '8px',
            'padding': '8px',
            'backgroundColor': 'white',
            'marginTop': '16px'
        })
    ])

    # Cache and return
    _home_layout_cache = layout
    _home_layout_cache_ts = time.time()
    return layout

layout = serve_layout


def _format_minutes_to_human(minutes: float) -> str:
    try:
        m = float(minutes or 0.0)
        if m < 60:
            return f"{m:.0f} Min"
        h = m / 60.0
        if h < 24:
            return f"{h:.1f} Std"
        d = h / 24.0
        return f"{d:.1f} Tg"
    except Exception:
        return "0 Min"


@callback(
    Output('ci-all-table-container', 'children'),
    [Input('incidents-data-store', 'data')]
)
def render_ci_all_table(_):
    try:
        # Daten inkl. Downtimes aus DB laden
        df = get_all_cis_with_downtimes()
        if df is None or df.empty:
            return html.Div('Keine CIs verfügbar.')

        # Sortierung nach CI sicherstellen (Server-seitig schon sortiert)
        try:
            df = df.copy()
            df['ci'] = df['ci'].astype(str)
            df = df.sort_values('ci')
        except Exception:
            pass

        # Nur ersten 5 Zeilen anzeigen (Container ist scrollbar)
        try:
            df_display = df.head(5)
        except Exception:
            df_display = df

        # Tabellenzeilen bauen
        rows = []
        for _, row in df_display.iterrows():
            status = int(row.get('current_availability') or 0)
            status_class = 'available' if status == 1 else 'unavailable'
            status_text = 'Verfügbar' if status == 1 else 'Gestört'

            rows.append(html.Tr([
                html.Td([
                    html.A(str(row.get('ci', '')), href=f"/plot?ci={str(row.get('ci',''))}", className='ci-link'),
                    html.Br(),
                    html.Span(str(row.get('name', '')), className='ci-name')
                ]),
                html.Td([
                    html.Span(str(row.get('organization', '')), className='org-name'),
                    html.Br(),
                    html.Span(str(row.get('product', '')), className='product-name')
                ]),
                html.Td(_format_minutes_to_human(row.get('downtime_7d_min'))),
                html.Td(_format_minutes_to_human(row.get('downtime_30d_min'))),
                html.Td(html.Span(status_text, className=f'status-badge {status_class}'))
            ]))

        table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th('CI'),
                    html.Th('Organisation · Produkt'),
                    html.Th('Downtime 7 Tage'),
                    html.Th('Downtime 30 Tage'),
                    html.Th('Status')
                ])
            ]),
            html.Tbody(rows)
        ], className='ci-all-table')

        return table
    except Exception as e:
        return html.Div(f'Fehler beim Laden der CI-Tabelle: {str(e)}', style={'color': 'red'})
