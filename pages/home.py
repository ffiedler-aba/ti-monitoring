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

# Clientside callback for incidents table toggle
clientside_callback(
    """
    function(n_clicks, incidents_data) {
        if (!incidents_data || incidents_data.length === 0) {
            return window.dash_clientside.no_update;
        }
        
        const showAll = n_clicks % 2 === 1;
        const displayIncidents = showAll ? incidents_data : incidents_data.slice(0, 5);
        
        // Create table rows
        let tableRows = '';
        displayIncidents.forEach(incident => {
            const statusClass = incident.status === 'ongoing' ? 'incident-ongoing' : 'incident-resolved';
            const statusText = incident.status === 'ongoing' ? 'Noch gestört' : 'Wieder aktiv';
            
            // Format duration
            const durationHours = incident.duration_minutes / 60.0;
            const durationText = durationHours < 1 ? 
                `${incident.duration_minutes.toFixed(0)} Min` : 
                `${durationHours.toFixed(1)} Std`;
            
            // Format timestamps
            const startTime = new Date(incident.incident_start).toLocaleString('de-DE', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            const endTime = incident.incident_end ? 
                new Date(incident.incident_end).toLocaleString('de-DE', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }) : 'Laufend';
            
            tableRows += `
                <tr>
                    <td>
                        <a href="/plot?ci=${incident.ci}" class="ci-link">${incident.ci}</a><br>
                        <span class="ci-name">${incident.name}</span>
                    </td>
                    <td>
                        <span class="org-name">${incident.organization}</span><br>
                        <span class="product-name">${incident.product}</span>
                    </td>
                    <td class="timestamp">${startTime}</td>
                    <td class="timestamp">${endTime}</td>
                    <td class="duration">${durationText}</td>
                    <td>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </td>
                </tr>
            `;
        });
        
        const buttonText = showAll ? 'Nur 5 anzeigen' : 'Alle anzeigen';
        const buttonHtml = incidents_data.length > 5 ? 
            `<button class="incidents-expand-btn" style="margin-top: 15px; padding: 8px 16px; background-color: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.3s ease;">${buttonText}</button>` : '';
        
        return `
            <table class="incidents-table">
                <thead>
                    <tr>
                        <th>CI</th>
                        <th>Organisation</th>
                        <th>Beginn</th>
                        <th>Ende</th>
                        <th>Dauer</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${tableRows}
                </tbody>
            </table>
            ${buttonHtml}
        `;
    }
    """,
    Output('incidents-table-container', 'children'),
    Input('incidents-expand-btn', 'n_clicks'),
    State('incidents-data-store', 'data')
)

def create_incidents_table(incidents_data, show_all=False):
    """Erstellt eine erweiterbare Tabelle mit den letzten Incidents"""
    if not incidents_data:
        return html.P("Keine Incidents verfügbar.")
    
    # Limit incidents based on show_all parameter
    display_incidents = incidents_data if show_all else incidents_data[:5]
    
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
    
    # Create expand button if there are more than 5 incidents
    expand_button = None
    if len(incidents_data) > 5:
        expand_button = html.Button(
            'Alle anzeigen' if not show_all else 'Nur 5 anzeigen',
            className='incidents-expand-btn',
            style={
                'marginTop': '15px',
                'padding': '8px 16px',
                'backgroundColor': '#3498db',
                'color': 'white',
                'border': 'none',
                'borderRadius': '6px',
                'cursor': 'pointer',
                'fontSize': '0.85rem',
                'fontWeight': '500',
                'transition': 'all 0.3s ease'
            }
        )
    
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
        ], className='incidents-table'),
        expand_button
    ])

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
                ]) for _, row in group_data.iterrows()
            ])
        ])
    ])



def serve_layout():
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
    
    layout = html.Div([
        html.P('Hier finden Sie eine nach Produkten gruppierte Übersicht sämtlicher TI-Komponenten. Neue Daten werden alle 5 Minuten bereitgestellt. Laden Sie die Seite neu, um die Ansicht zu aktualisieren.'),
        
        # Incidents section
        html.Div([
            html.H3("Letzte Incidents", className='incidents-title'),
            html.Div([
                dcc.Store(id='incidents-data-store', data=incidents_data),
                html.Div(id='incidents-table-container', children=incidents_table)
            ], className='incidents-container')
        ], className='incidents-section'),
        
        # CI Groups section
        html.Div([
            html.H3("TI-Komponenten nach Produkten", className='groups-title'),
            html.Div(className='accordion', children=accordion_elements)
        ], className='groups-section')
    ])
    
    return layout

layout = serve_layout