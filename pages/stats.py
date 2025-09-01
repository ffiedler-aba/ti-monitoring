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

# Configuration cache for stats page with size limit
_stats_config_cache = {}
_stats_config_cache_timestamp = 0
_stats_config_cache_ttl = 300  # 5 seconds cache TTL
_stats_config_cache_max_size = 10  # Limit cache size

# Statistics cache for performance optimization
_stats_data_cache = {}
_stats_data_cache_timestamp = 0
_stats_data_cache_ttl = 300  # 5 minutes cache TTL for statistics

def load_config():
    """Load configuration from YAML file with caching"""
    global _stats_config_cache, _stats_config_cache_timestamp
    
    current_time = time.time()
    if (not _stats_config_cache or 
        current_time - _stats_config_cache_timestamp > _stats_config_cache_ttl):
        
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                _stats_config_cache = yaml.safe_load(f) or {}
            _stats_config_cache_timestamp = current_time
            
            # Limit cache size
            if len(_stats_config_cache) > _stats_config_cache_max_size:
                # Keep only the most recent entries
                keys = list(_stats_config_cache.keys())[:_stats_config_cache_max_size]
                _stats_config_cache = {k: _stats_config_cache[k] for k in keys}
        except (FileNotFoundError, Exception):
            _stats_config_cache = {}
            _stats_config_cache_timestamp = current_time
    
    return _stats_config_cache

def load_core_config():
    """Load core configuration from cached config"""
    config = load_config()
    return config.get('core', {})

def get_cached_statistics(config_file_name, cis):
    """Get statistics from cache or calculate them if cache is expired"""
    global _stats_data_cache, _stats_data_cache_timestamp
    
    current_time = time.time()
    
    # Check if cache is valid
    if (_stats_data_cache and 
        current_time - _stats_data_cache_timestamp < _stats_data_cache_ttl):
        print(f"Using cached statistics (cache age: {current_time - _stats_data_cache_timestamp:.1f}s)")
        return _stats_data_cache
    
    # Cache expired or empty, calculate new statistics
    print("Calculating new statistics (cache expired or empty)")
    new_stats = calculate_overall_statistics(config_file_name, cis)
    
    # Update cache
    _stats_data_cache = new_stats
    _stats_data_cache_timestamp = current_time
    
    return new_stats

def clear_statistics_cache():
    """Clear the statistics cache (useful for debugging or manual refresh)"""
    global _stats_data_cache, _stats_data_cache_timestamp
    _stats_data_cache = {}
    _stats_data_cache_timestamp = 0
    print("Statistics cache cleared")

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
    - Total downtime statistics across all CIs
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
    
    # Calculate total downtime statistics across all CIs
    total_downtime_minutes = 0
    total_uptime_minutes = 0
    
    # Calculate total recording time from the overall time range (more accurate)
    if latest_timestamp and earliest_timestamp:
        total_recording_minutes = (latest_timestamp - earliest_timestamp).total_seconds() / 60
        print(f"Total recording time: {earliest_timestamp} to {latest_timestamp} = {total_recording_minutes:.1f} minutes")
    else:
        total_recording_minutes = 0
    
    try:
        # Import the function here to avoid circular imports
        from mylibrary import get_availability_data_of_ci
        
        # Take a sample of CIs to calculate downtime (max 20 CIs to avoid performance issues)
        sample_size = min(20, len(cis))
        if sample_size > 0:
            # Take a representative sample
            sample_cis = cis.sample(n=sample_size, random_state=42)  # Fixed seed for consistency
            
            print(f"Calculating downtime statistics for sample of {sample_size} CIs out of {len(cis)} total")
            
            # Calculate total downtime for sample CIs
            for _, ci_row in sample_cis.iterrows():
                ci_id = ci_row['ci']
                try:
                    # Get availability data for this CI
                    ci_availability = get_availability_data_of_ci(config_file_name, ci_id)
                    if not ci_availability.empty:
                        # Count downtime and uptime (assuming 5-minute intervals)
                        downtime_count = (ci_availability['values'] == 0).sum()
                        uptime_count = (ci_availability['values'] == 1).sum()
                        
                        # Convert to minutes
                        total_downtime_minutes += downtime_count * 5
                        total_uptime_minutes += uptime_count * 5
                        
                except Exception as e:
                    print(f"Warning: Could not calculate downtime for CI {ci_id}: {e}")
                    continue
            
            # Scale up the downtime/uptime results to estimate total across all CIs
            if sample_size > 0:
                scale_factor = len(cis) / sample_size
                total_downtime_minutes *= scale_factor
                total_uptime_minutes *= scale_factor
                
                print(f"Scaled downtime/uptime by factor {scale_factor:.2f} to estimate totals")
        
        # Convert to various time units
        total_downtime_hours = total_downtime_minutes / 60
        total_downtime_days = total_downtime_hours / 24
        total_downtime_weeks = total_downtime_days / 7
        total_downtime_years = total_downtime_days / 365.25
        
        total_uptime_hours = total_uptime_minutes / 60
        total_uptime_days = total_uptime_hours / 24
        
        # Calculate overall availability percentage based on total time
        if total_recording_minutes > 0:
            overall_availability_percentage_total = (total_uptime_minutes / total_recording_minutes) * 100
        else:
            overall_availability_percentage_total = 0
            
        # Calculate average downtime per time interval based on total recording duration
        if total_recording_minutes > 0:
            # Calculate average downtime per day/week/year based on recording duration
            recording_days = total_recording_minutes / (24 * 60)
            recording_weeks = recording_days / 7
            recording_years = recording_days / 365.25
            
            if recording_days > 0:
                # Average downtime per day/week/year over the entire recording period
                downtime_per_day = total_downtime_minutes / recording_days
                downtime_per_week = total_downtime_minutes / recording_weeks
                downtime_per_year = total_downtime_minutes / recording_years
            else:
                downtime_per_day = downtime_per_week = downtime_per_year = 0
        else:
            downtime_per_day = downtime_per_week = downtime_per_year = 0
            
    except Exception as e:
        print(f"Warning: Could not calculate comprehensive downtime statistics: {e}")
        # Set default values if calculation fails
        total_downtime_minutes = total_downtime_hours = total_downtime_days = 0
        total_downtime_weeks = total_downtime_years = 0
        total_uptime_minutes = total_uptime_hours = total_uptime_days = 0
        overall_availability_percentage_total = overall_availability_percentage
        downtime_per_day = downtime_per_week = downtime_per_year = 0
    
    return {
        'total_cis': total_cis,
        'currently_available': currently_available,
        'currently_unavailable': currently_unavailable,
        'overall_availability_percentage': overall_availability_percentage,
        'overall_availability_percentage_total': overall_availability_percentage_total,
        'total_products': total_products,
        'total_organizations': total_organizations,
        'available_count': available_count,
        'unavailable_count': unavailable_count,
        'changes_count': changes_count,
        'latest_timestamp': latest_timestamp,
        'earliest_timestamp': earliest_timestamp,
        'data_age_formatted': data_age_formatted,
        'product_counts': product_counts,
        'organization_counts': organization_counts,
        'total_downtime_minutes': total_downtime_minutes,
        'total_downtime_hours': total_downtime_hours,
        'total_downtime_days': total_downtime_days,
        'total_downtime_weeks': total_downtime_weeks,
        'total_downtime_years': total_downtime_years,
        'total_uptime_minutes': total_uptime_minutes,
        'total_uptime_hours': total_uptime_hours,
        'total_uptime_days': total_uptime_days,
        'total_recording_minutes': total_recording_minutes,
        'downtime_per_day': downtime_per_day,
        'downtime_per_week': downtime_per_week,
        'downtime_per_year': downtime_per_year
    }

dash.register_page(__name__, path='/stats')

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
    
    # Add comprehensive availability statistics
    if stats.get('total_recording_minutes', 0) > 0:
        children.append(
            html.Div(className='comprehensive-availability', children=[
                html.H4('⏱️ Gesamtverfügbarkeit über alle CIs'),
                html.Div(className='stat-grid', children=[
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtverfügbarkeit (Zeitbasis): '),
                        html.Span(f'{stats["overall_availability_percentage_total"]:.1f}%')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtaufzeichnungszeit: '),
                        html.Span(format_duration(stats["total_recording_minutes"] / 60))
                    ])
                ])
            ])
        )
    
    # Add total downtime statistics
    if stats.get('total_downtime_minutes', 0) > 0:
        children.append(
            html.Div(className='total-downtime', children=[
                html.H4('🔴 Summierte Ausfallzeiten aller CIs'),
                html.Div(className='stat-grid', children=[
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtausfallzeit: '),
                        html.Span(format_duration(stats["total_downtime_hours"]))
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtausfallzeit (⌀ pro Tag): '),
                        html.Span(f'{stats["total_downtime_days"]:.3f} Tage' if stats["total_downtime_days"] >= 0.001 else f'{stats["total_downtime_days"]:.6f} Tage')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtausfallzeit (⌀ pro Woche): '),
                        html.Span(f'{stats["total_downtime_weeks"]:.3f} Wochen' if stats["total_downtime_weeks"] >= 0.001 else f'{stats["total_downtime_weeks"]:.6f} Wochen')
                    ]),
                    html.Div(className='stat-item', children=[
                        html.Strong('Gesamtausfallzeit (⌀ pro Jahr): '),
                        html.Span(f'{stats["total_downtime_years"]:.4f} Jahre' if stats["total_downtime_years"] >= 0.001 else f'{stats["total_downtime_years"]:.6f} Jahre')
                    ])
                ])
            ])
        )
        
        # Add average downtime per time interval
        if stats.get('downtime_per_day', 0) > 0:
            children.append(
                html.Div(className='downtime-projections', children=[
                    html.H4('📈 Durchschnittliche Ausfallzeiten pro Zeitintervall'),
                    html.Div(className='stat-grid', children=[
                        html.Div(className='stat-item', children=[
                            html.Strong('Durchschnittliche Ausfallzeit pro Tag: '),
                            html.Span(format_duration(stats["downtime_per_day"] / 60))
                        ]),
                        html.Div(className='stat-item', children=[
                            html.Strong('Durchschnittliche Ausfallzeit pro Woche: '),
                            html.Span(format_duration(stats["downtime_per_week"] / 60))
                        ]),
                        html.Div(className='stat-item', children=[
                            html.Strong('Durchschnittliche Ausfallzeit pro Jahr: '),
                            html.Span(format_duration(stats["downtime_per_year"] / 60))
                        ])
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
    
    # Get statistics from cache or calculate them
    overall_stats = get_cached_statistics(config_file_name, cis)
    
    # Force garbage collection periodically to prevent memory buildup
    if int(time.time()) % 300 == 0:  # Every 5 minutes
        gc.collect()
    
    layout = html.Div([
        html.P('Hier finden Sie eine umfassende Gesamtstatistik aller Configuration Items mit detaillierten Ausfallzeit-Analysen. Neue Daten werden alle 5 Minuten bereitgestellt. Laden Sie die Seite neu, um die Ansicht zu aktualisieren.'),
        
        # Cache information
        html.Div(className='cache-info', children=[
            html.P(f'📊 Statistiken wurden zuletzt berechnet: {pd.Timestamp.fromtimestamp(_stats_data_cache_timestamp, tz="Europe/Berlin").strftime("%d.%m.%Y %H:%M:%S")} Uhr'),
            html.P(f'⏰ Cache läuft ab in: {_stats_data_cache_ttl - (time.time() - _stats_data_cache_timestamp):.0f} Sekunden')
        ]),
        
        # Overall statistics section
        create_overall_statistics_display(overall_stats)
    ])
    
    return layout

layout = serve_layout
