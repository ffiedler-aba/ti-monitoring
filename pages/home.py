import dash
from dash import html
from mylibrary import *
from myconfig import *
import yaml
import os
import functools
import time
import gc
import pandas as pd
import numpy as np
import pytz

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

def calculate_overall_statistics(config_file_name, cis):
    """
    Calculate overall statistics for all Configuration Items including:
    - Total counts and current availability
    - Overall availability percentage
    - Recording time range
    - Product distribution
    - Organization distribution
    """
    if cis.empty:
        return {}
    
    # Basic counts
    total_cis = len(cis)
    currently_available = cis['current_availability'].sum()
    currently_unavailable = total_cis - currently_available
    overall_availability_percentage = (currently_available / total_cis) * 100 if total_cis > 0 else 0
    
    # Product distribution
    product_counts = cis['product'].value_counts()
    total_products = len(product_counts)
    
    # Organization distribution
    organization_counts = cis['organization'].value_counts()
    total_organizations = len(organization_counts)
    
    # Current status distribution
    status_counts = cis['current_availability'].value_counts()
    available_count = status_counts.get(1, 0)
    unavailable_count = status_counts.get(0, 0)
    
    # Recent changes (availability_difference != 0)
    recent_changes = cis[cis['availability_difference'] != 0]
    changes_count = len(recent_changes)
    
    # Get overall recording time range (from the most recent timestamp)
    if 'time' in cis.columns:
        latest_timestamp = pd.to_datetime(cis['time'].max())
        earliest_timestamp = pd.to_datetime(cis['time'].min())
        
        # Ensure both timestamps have timezone info and are in Europe/Berlin
        if latest_timestamp.tz is None:
            latest_timestamp = latest_timestamp.tz_localize('Europe/Berlin')
        elif latest_timestamp.tz != pytz.timezone('Europe/Berlin'):
            latest_timestamp = latest_timestamp.tz_convert('Europe/Berlin')
            
        if earliest_timestamp.tz is None:
            earliest_timestamp = earliest_timestamp.tz_localize('Europe/Berlin')
        elif earliest_timestamp.tz != pytz.timezone('Europe/Berlin'):
            earliest_timestamp = earliest_timestamp.tz_convert('Europe/Berlin')
        
        # Get current time in Europe/Berlin
        current_time = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin'))
        data_age_hours = (current_time - latest_timestamp).total_seconds() / 3600
        data_age_formatted = format_duration(data_age_hours)
    else:
        latest_timestamp = None
        earliest_timestamp = None
        data_age_formatted = "Unbekannt"
    
    return {
        'total_cis': total_cis,
        'currently_available': currently_available,
        'currently_unavailable': currently_unavailable,
        'overall_availability_percentage': overall_availability_percentage,
        'total_products': total_products,
        'total_organizations': total_organizations,
        'available_count': available_count,
        'unavailable_count': unavailable_count,
        'changes_count': changes_count,
        'latest_timestamp': latest_timestamp,
        'earliest_timestamp': earliest_timestamp,
        'data_age_formatted': data_age_formatted,
        'product_counts': product_counts,
        'organization_counts': organization_counts
    }

dash.register_page(__name__, path='/')

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

def create_overall_statistics_display(stats):
    """Create the overall statistics display section"""
    children = [
        html.H3('📊 Gesamtstatistik aller Configuration Items'),
        
        # Main overview
        html.Div(className='stats-overview', children=[
            html.Div(className='stat-card', children=[
                html.H4('🎯 Übersicht'),
                html.Div(className='stat-grid', children=[
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtanzahl CIs: '),
                        html.Span(f'{stats["total_cis"]:,}')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Aktuell verfügbar: '),
                        html.Span(f'{stats["currently_available"]:,}')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Aktuell nicht verfügbar: '),
                        html.Span(f'{stats["currently_unavailable"]:,}')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtverfügbarkeit: '),
                        html.Span(f'{stats["overall_availability_percentage"]:.1f}%')
                    ])
                ])
            ]),
            
            html.Div(className='stat-card', children=[
                html.H4('📅 Datenstatus'),
                html.Div(className='stat-grid', children=[
                    html.Div(className='stat-item', children=[
                        html.Strong('Letzte Aktualisierung: '),
                        html.Span(stats["latest_timestamp"].strftime('%d.%m.%Y %H:%M:%S Uhr') if stats["latest_timestamp"] else 'Unbekannt')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Datenalter: '),
                        html.Span(stats["data_age_formatted"])
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Kürzliche Änderungen: '),
                        html.Span(f'{stats["changes_count"]:,}')
                    ])
                ])
            ]),
            
            html.Div(className='stat-card', children=[
                html.H4('🏢 Struktur'),
                html.Div(className='stat-grid', children=[
                    html.Div(className='stat-item', children=[
                        html.Strong('Produkte: '),
                        html.Span(f'{stats["total_products"]:,}')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Organisationen: '),
                        html.Span(f'{stats["total_organizations"]:,}')
                    ])
                ])
            ])
        ])
    ]
    
    # Add top products if available
    if len(stats["product_counts"]) > 0:
        children.append(
            html.Div(className='top-products', children=[
                html.H4('🏆 Top Produkte (nach Anzahl CIs)'),
                html.Div(className='product-list', children=[
                    html.Div(className='product-item', children=[
                        html.Strong(f'{product}: '),
                        html.Span(f'{count:,} CIs')
                    ]) for product, count in stats["product_counts"].head(5).items()
                ])
            ])
        )
    
    # Add top organizations if available
    if len(stats["organization_counts"]) > 0:
        children.append(
            html.Div(className='top-organizations', children=[
                html.H4('🏢 Top Organisationen (nach Anzahl CIs)'),
                html.Div(className='organization-list', children=[
                    html.Div(className='organization-item', children=[
                        html.Strong(f'{org}: '),
                        html.Span(f'{count:,} CIs')
                    ]) for org, count in stats["organization_counts"].head(5).items()
                ])
            ])
        )
    
    return html.Div(className='overall-statistics box', children=children)

def serve_layout():
    # Load core configurations (now cached)
    core_config = load_core_config()
    
    # Get file_name from YAML as primary source, fallback to myconfig.py
    config_file_name = core_config.get('file_name') or file_name
    config_url = core_config.get('url')
    
    # Check if data file exists and initialize if needed
    if not os.path.exists(config_file_name):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(config_file_name), exist_ok=True)
            # Initialize empty data file
            initialize_data_file(config_file_name)
            print(f"Initialized data file: {config_file_name}")
        except Exception as e:
            print(f"Error initializing data file: {e}")
    
    # Try to get data
    try:
        cis = get_data_of_all_cis(config_file_name)
    except Exception as e:
        print(f"Error reading data: {e}")
        cis = pd.DataFrame()  # Empty DataFrame
    
    # Check if DataFrame is empty
    if cis.empty:
        # Try to load data from API if URL is available
        if config_url:
            try:
                print(f"Loading data from API: {config_url}")
                update_file(config_file_name, config_url)
                # Try to read data again
                cis = get_data_of_all_cis(config_file_name)
                print(f"Loaded {len(cis)} records from API")
            except Exception as e:
                print(f"Error loading data from API: {e}")
        
        # If still empty, show message
        if cis.empty:
            layout = html.Div([
                html.P('Keine Daten verfügbar. Versuche Daten von der API zu laden...'),
                html.P('Falls das Problem weiterhin besteht, überprüfen Sie die API-Verbindung.'),
                html.P(f'API URL: {config_url or "Nicht konfiguriert"}'),
                html.P(f'Daten-Datei: {config_file_name}')
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
    
    # Calculate overall statistics
    overall_stats = calculate_overall_statistics(config_file_name, cis)
    
    # Create accordion elements efficiently
    accordion_elements = []
    for group_name, group_data in grouped:
        accordion_elements.append(create_accordion_element(group_name, group_data))
    
    # Force garbage collection periodically to prevent memory buildup
    if int(time.time()) % 300 == 0:  # Every 5 minutes
        gc.collect()
    
    layout = html.Div([
        html.P('Hier finden Sie eine nach Produkten gruppierte Übersicht sämtlicher TI-Komponenten. Neue Daten werden alle 5 Minuten bereitgestellt. Laden Sie die Seite neu, um die Ansicht zu aktualisieren.'),
        html.Div(className='accordion', children=accordion_elements),
        
        # Overall statistics section (below the accordion)
        create_overall_statistics_display(overall_stats)
    ])
    
    return layout

layout = serve_layout