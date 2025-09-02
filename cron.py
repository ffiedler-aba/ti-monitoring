# Import packages
from mylibrary import *
import yaml
import os
import time
import gc
import sys
import json
import pandas as pd
import numpy as np
import pytz
import h5py

# Enhanced logging setup with file logging and daily rotation
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os

# Global logger instance
_logger = None

def setup_logger():
    """Setup logger with file rotation and console output"""
    global _logger
    
    if _logger is not None:
        return _logger
    
    try:
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Setup logger
        _logger = logging.getLogger('cron')
        _logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        _logger.handlers.clear()
        
        # Create formatter with timezone
        class TimezoneFormatter(logging.Formatter):
            def formatTime(self, record, datefmt=None):
                # Convert to Europe/Berlin timezone
                dt = datetime.fromtimestamp(record.created, tz=pytz.timezone('Europe/Berlin'))
                if datefmt:
                    return dt.strftime(datefmt)
                else:
                    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        
        formatter = TimezoneFormatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S %Z')
        
        # File handler with daily rotation
        log_file = os.path.join(data_dir, 'cron.log')
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=7,  # Keep 7 days of logs
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        _logger.propagate = False
        
        return _logger
        
    except Exception as e:
        # Fallback to simple print if logging setup fails
        print(f"ERROR setting up logger: {e}")
        return None

def log(message):
    """Enhanced logging function with file logging and daily rotation"""
    try:
        # Ensure message is a string
        if not isinstance(message, str):
            message = str(message)
        
        # Setup logger if not already done
        if _logger is None:
            setup_logger()
        
        # Log to file and console
        if _logger is not None:
            _logger.info(message)
        else:
            # Fallback to console only
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] {message}")
            sys.stdout.flush()
            
    except Exception as e:
        # Fallback logging if the main logging fails
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] [LOGGING_ERROR] {e} - Original message: {message}")
            sys.stdout.flush()
        except:
            # If even fallback fails, we can't do much more
            pass

def load_config():
    """Load configuration from YAML file with comprehensive error handling"""
    try:
        log("Starting configuration loading...")
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        log(f"Config path: {config_path}")
        log(f"Current working directory: {os.getcwd()}")
        log(f"Config file exists: {os.path.exists(config_path)}")
        
        if not os.path.exists(config_path):
            log(f"ERROR: Config file not found: {config_path}")
            return {}
        
        # Check file size to avoid loading huge files
        file_size = os.path.getsize(config_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            log(f"ERROR: Config file too large: {file_size} bytes")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            log("WARNING: Configuration file is empty or invalid")
            return {}
            
        log(f"Configuration loaded successfully. Keys: {list(config.keys())}")
        return config
        
    except FileNotFoundError as e:
        log(f"ERROR: Config file not found: {e}")
        return {}
    except yaml.YAMLError as e:
        log(f"ERROR: Invalid YAML syntax: {e}")
        return {}
    except PermissionError as e:
        log(f"ERROR: Permission denied reading config file: {e}")
        return {}
    except Exception as e:
        log(f"ERROR: Failed to load config: {e}")
        return {}

def load_core_config():
    """Load core configuration from YAML file with comprehensive error handling"""
    try:
        log("Loading core configuration...")
        config = load_config()
        if not config:
            log("WARNING: Empty configuration loaded")
            return {}
        
        core_config = config.get('core', {})
        if not core_config:
            log("WARNING: No 'core' section found in configuration")
            return {}
            
        log(f"Core config loaded. Keys: {list(core_config.keys())}")
        return core_config
        
    except Exception as e:
        log(f"ERROR loading core configuration: {e}")
        return {}

def update_ci_list_file(config_file_name, ci_list_file_path):
    """Update the CI list file with current configuration items"""
    try:
        log(f"Updating CI list file: {ci_list_file_path}")
        
        # Validate inputs
        if not config_file_name:
            log("ERROR: config_file_name is empty or None")
            return False
            
        if not ci_list_file_path:
            log("ERROR: ci_list_file_path is empty or None")
            return False
        
        # Check if config file exists
        if not os.path.exists(config_file_name):
            log(f"ERROR: Config file does not exist: {config_file_name}")
            return False
        
        # Get all CIs from the data file with error handling
        try:
            cis_df = get_data_of_all_cis(config_file_name)
        except Exception as e:
            log(f"ERROR getting CI data: {e}")
            return False
        
        if cis_df.empty:
            log("No CIs found in data file")
            return False
        
        # Convert to list of dictionaries with relevant information
        try:
            ci_list = []
            for _, row in cis_df.iterrows():
                try:
                    ci_info = {
                        'ci': str(row.get('ci', '')),
                        'name': str(row.get('name', '')),
                        'organization': str(row.get('organization', '')),
                        'product': str(row.get('product', '')),
                        'tid': str(row.get('tid', '')),
                        'bu': str(row.get('bu', '')),
                        'pdt': str(row.get('pdt', ''))
                    }
                    ci_list.append(ci_info)
                except Exception as e:
                    log(f"Warning: Error processing CI row: {e}")
                    continue
        except Exception as e:
            log(f"ERROR processing CI data: {e}")
            return False
        
        if not ci_list:
            log("ERROR: No valid CIs found after processing")
            return False
        
        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(ci_list_file_path), exist_ok=True)
        except Exception as e:
            log(f"ERROR creating CI list directory: {e}")
            return False
        
        # Write to JSON file with comprehensive error handling
        try:
            # Create backup of existing file if it exists
            if os.path.exists(ci_list_file_path):
                backup_path = ci_list_file_path + '.backup'
                try:
                    import shutil
                    shutil.copy2(ci_list_file_path, backup_path)
                    log(f"Created backup: {backup_path}")
                except Exception as e:
                    log(f"Warning: Could not create backup: {e}")
            
            # Write new CI list file
            with open(ci_list_file_path, 'w', encoding='utf-8') as f:
                json.dump(ci_list, f, ensure_ascii=False, indent=2)
            
            # Verify the file was written correctly
            if os.path.exists(ci_list_file_path) and os.path.getsize(ci_list_file_path) > 0:
                log(f"CI list file updated successfully with {len(ci_list)} CIs")
                return True
            else:
                log("ERROR: CI list file was not written correctly")
                return False
                
        except Exception as e:
            log(f"ERROR writing CI list file: {e}")
            # Try to restore backup if it exists
            backup_path = ci_list_file_path + '.backup'
            if os.path.exists(backup_path):
                try:
                    import shutil
                    shutil.copy2(backup_path, ci_list_file_path)
                    log(f"Restored backup file: {backup_path}")
                except Exception as e:
                    log(f"ERROR restoring backup: {e}")
            return False
            
    except Exception as e:
        log(f"FATAL ERROR in update_ci_list_file: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        return False







def calculate_recording_duration(config_file_name):
    """Calculate the total recording duration from availability data"""
    try:
        if not os.path.exists(config_file_name):
            log(f"Data file not found: {config_file_name}")
            return 0, None, None
        
        with h5py.File(config_file_name, 'r', swmr=True) as f:
            if 'availability' not in f:
                log("No availability group found in data file")
                return 0, None, None
            
            availability_group = f['availability']
            total_ci_count = 0
            total_ts_count = 0
            min_epoch = None
            
            # Stream-only min over all CI timestamp keys (avoid per-item tz conversion & list)
            for ci_name in availability_group.keys():
                ci_group = availability_group[ci_name]
                total_ci_count += 1
                for timestamp_str in ci_group.keys():
                    try:
                        epoch_val = float(timestamp_str)
                    except Exception:
                        # Skip invalid keys
                        continue
                    total_ts_count += 1
                    if (min_epoch is None) or (epoch_val < min_epoch):
                        min_epoch = epoch_val
            
            log(f"Collected {total_ts_count} timestamps from {total_ci_count} CIs")
            
            if (min_epoch is not None):
                earliest_timestamp = pd.to_datetime(min_epoch, unit='s').tz_localize('UTC').tz_convert('Europe/Berlin')
                current_time = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin'))
                total_recording_minutes = (current_time.timestamp() - min_epoch) / 60
                log(f"Approx. recording time (earliest to now): {earliest_timestamp} to {current_time} = {total_recording_minutes:.1f} minutes ({total_recording_minutes/60/24:.1f} days)")
                return total_recording_minutes, earliest_timestamp, current_time
            else:
                log("No timestamps found in availability data")
                return 0, None, None
                
    except Exception as e:
        log(f"Error calculating recording duration: {e}")
        return 0, None, None

def compute_incident_and_availability_metrics(config_file_name):
    """
    Compute per-CI and aggregated availability metrics using availability time series in HDF5.
    - Treat each timestamp's value (0/1) as status until the next timestamp (right-open interval).
    - For the last timestamp, extend interval to 'now'.
    - Incidents are 1->0 transitions; repair is 0->1.
    Returns dict with rollups and per_ci details.
    """
    metrics = {
        'overall_uptime_minutes': 0.0,
        'overall_downtime_minutes': 0.0,
        'overall_availability_percentage_rollup': 0.0,
        'total_incidents': 0,
        'mttr_minutes_mean': 0.0,
        'mtbf_minutes_mean': 0.0,
        'top_unstable_cis_by_incidents': [],
        'top_downtime_cis': [],
        'per_ci_metrics': {}
    }
    try:
        if not os.path.exists(config_file_name):
            return metrics
        now_epoch = time.time()
        with h5py.File(config_file_name, 'r', swmr=True) as f:
            if 'availability' not in f:
                return metrics
            availability_group = f['availability']
            # Enrich CI metadata (name, organization) from general CI data
            ci_metadata = {}
            try:
                cis_df = get_data_of_all_cis(config_file_name)
                if not cis_df.empty and all(c in cis_df.columns for c in ['ci','name','organization']):
                    for _, row in cis_df[['ci','name','organization']].iterrows():
                        ci_metadata[str(row['ci'])] = {
                            'name': str(row['name']) if not pd.isna(row['name']) else '',
                            'organization': str(row['organization']) if not pd.isna(row['organization']) else ''
                        }
            except Exception as e:
                log(f"Warning: could not enrich CI metadata: {e}")
            per_ci_results = {}
            total_downtime_list = []
            total_mttr_values = []
            total_mtbf_values = []
            total_incidents = 0
            overall_uptime = 0.0
            overall_downtime = 0.0
            for ci_name in availability_group.keys():
                ci_group = availability_group[ci_name]
                # Collect and sort all timestamps as floats
                ts_list = []
                for k in ci_group.keys():
                    try:
                        ts_list.append(float(k))
                    except Exception:
                        continue
                if not ts_list:
                    continue
                ts_list.sort()
                # Build status sequence aligned to ts_list
                statuses = []
                for ts in ts_list:
                    try:
                        ds = ci_group[str(ts)]
                        val = int(ds[()]) if isinstance(ds, h5py.Dataset) else int(ds)
                        statuses.append(1 if val != 0 else 0)
                    except Exception:
                        statuses.append(0)
                # Compute intervals
                downtime_minutes = 0.0
                uptime_minutes = 0.0
                incidents = 0
                mttr_list = []
                mtbf_list = []
                current_state = statuses[0]
                last_change_epoch = ts_list[0]
                last_epoch = ts_list[0]
                # Track last up-period start for MTBF (time between incidents)
                last_repair_epoch = None
                for idx in range(len(ts_list) - 1):
                    start = ts_list[idx]
                    end = ts_list[idx + 1]
                    dur_min = (end - start) / 60.0
                    if statuses[idx] == 1:
                        uptime_minutes += dur_min
                    else:
                        downtime_minutes += dur_min
                    # Transition detection at idx+1 (state applies from ts_list[idx])
                    if statuses[idx + 1] != statuses[idx]:
                        # state changes at 'end'
                        prev_state = statuses[idx]
                        new_state = statuses[idx + 1]
                        if prev_state == 1 and new_state == 0:
                            incidents += 1
                            last_change_epoch = end
                            # end of an up period -> start of downtime; close MTBF if there was a prior repair
                            if last_repair_epoch is not None:
                                mtbf_list.append((end - last_repair_epoch) / 60.0)
                        elif prev_state == 0 and new_state == 1:
                            # repair completed: downtime from last_change to end
                            if last_change_epoch is not None:
                                mttr_list.append((end - last_change_epoch) / 60.0)
                            last_repair_epoch = end
                        current_state = new_state
                    last_epoch = end
                # Extend last interval to now
                if last_epoch < now_epoch:
                    tail_min = (now_epoch - last_epoch) / 60.0
                    if statuses[-1] == 1:
                        uptime_minutes += tail_min
                    else:
                        downtime_minutes += tail_min
                # If last state is down, we have an open incident; do not close MTTR until repair occurs
                availability_pct = (uptime_minutes / (uptime_minutes + downtime_minutes) * 100.0) if (uptime_minutes + downtime_minutes) > 0 else 0.0
                meta = ci_metadata.get(ci_name, {})
                ci_result = {
                    'incidents': int(incidents),
                    'uptime_minutes': float(uptime_minutes),
                    'downtime_minutes': float(downtime_minutes),
                    'availability_percentage': float(availability_pct),
                    'mttr_minutes_mean': float(np.mean(mttr_list)) if mttr_list else 0.0,
                    'mtbf_minutes_mean': float(np.mean(mtbf_list)) if mtbf_list else 0.0,
                    'longest_outage_minutes': float(max(mttr_list)) if mttr_list else ( (now_epoch - last_change_epoch) / 60.0 if statuses[-1] == 0 else 0.0 ),
                    'name': meta.get('name', ''),
                    'organization': meta.get('organization', '')
                }
                per_ci_results[ci_name] = ci_result
                total_incidents += incidents
                overall_uptime += uptime_minutes
                overall_downtime += downtime_minutes
                total_downtime_list.append((ci_name, downtime_minutes))
                if mttr_list:
                    total_mttr_values.extend(mttr_list)
                if mtbf_list:
                    total_mtbf_values.extend(mtbf_list)
            overall_pct = (overall_uptime / (overall_uptime + overall_downtime) * 100.0) if (overall_uptime + overall_downtime) > 0 else 0.0
            # Rankings
            top_unstable = sorted(((ci, per_ci_results[ci]['incidents']) for ci in per_ci_results), key=lambda x: x[1], reverse=True)[:10]
            top_downtime = sorted(total_downtime_list, key=lambda x: x[1], reverse=True)[:10]
            metrics.update({
                'overall_uptime_minutes': overall_uptime,
                'overall_downtime_minutes': overall_downtime,
                'overall_availability_percentage_rollup': overall_pct,
                'total_incidents': total_incidents,
                'mttr_minutes_mean': float(np.mean(total_mttr_values)) if total_mttr_values else 0.0,
                'mtbf_minutes_mean': float(np.mean(total_mtbf_values)) if total_mtbf_values else 0.0,
                'top_unstable_cis_by_incidents': [{'ci': ci, 'incidents': inc} for ci, inc in top_unstable],
                'top_downtime_cis': [{'ci': ci, 'downtime_minutes': mins} for ci, mins in top_downtime],
                'per_ci_metrics': per_ci_results
            })
    except Exception as e:
        log(f"Error computing availability metrics: {e}")
    return metrics

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
    
    # Get recording duration from availability data
    total_recording_minutes, earliest_timestamp, latest_timestamp = calculate_recording_duration(config_file_name)

    # Get database file size
    database_size_mb = 0
    try:
        if os.path.exists(config_file_name):
            database_size_bytes = os.path.getsize(config_file_name)
            database_size_mb = database_size_bytes / (1024 * 1024)
    except Exception as e:
        log(f"Error getting database file size: {e}")

    # Compute incident and availability metrics from HDF5 availability data
    availability_metrics = compute_incident_and_availability_metrics(config_file_name)
    
    # Get current time in Europe/Berlin
    current_time = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin'))
    if latest_timestamp:
        data_age_hours = (current_time - latest_timestamp).total_seconds() / 3600
        data_age_formatted = format_duration(data_age_hours)
    else:
        data_age_formatted = "Unbekannt"
    
    return {
        'total_cis': int(total_cis),
        'currently_available': int(currently_available),
        'currently_unavailable': int(currently_unavailable),
        'overall_availability_percentage': float(overall_availability_percentage),
        'overall_availability_percentage_total': float(overall_availability_percentage),  # Same as current availability for now
        'total_products': int(total_products),
        'total_organizations': int(total_organizations),
        'available_count': int(available_count),
        'unavailable_count': int(unavailable_count),
        'changes_count': int(changes_count),
        'latest_timestamp': latest_timestamp.isoformat() if latest_timestamp else None,
        'earliest_timestamp': earliest_timestamp.isoformat() if earliest_timestamp else None,
        'data_age_formatted': data_age_formatted,
        'product_counts': product_counts.to_dict(),
        'organization_counts': organization_counts.to_dict(),
        'total_recording_minutes': float(total_recording_minutes),
        'calculated_at': time.time(),
        # New metrics (availability/incidents)
        'overall_uptime_minutes': float(availability_metrics.get('overall_uptime_minutes', 0.0)),
        'overall_downtime_minutes': float(availability_metrics.get('overall_downtime_minutes', 0.0)),
        'overall_availability_percentage_rollup': float(availability_metrics.get('overall_availability_percentage_rollup', 0.0)),
        'total_incidents': int(availability_metrics.get('total_incidents', 0)),
        'mttr_minutes_mean': float(availability_metrics.get('mttr_minutes_mean', 0.0)),
        'mtbf_minutes_mean': float(availability_metrics.get('mtbf_minutes_mean', 0.0)),
        'top_unstable_cis_by_incidents': availability_metrics.get('top_unstable_cis_by_incidents', []),
        'top_downtime_cis': availability_metrics.get('top_downtime_cis', []),
        'per_ci_metrics': availability_metrics.get('per_ci_metrics', {}),
        'database_size_mb': float(database_size_mb)
    }

def update_statistics_file(config_file_name):
    """Update the statistics JSON file with current data"""
    try:
        # Get current CI data
        cis = get_data_of_all_cis(config_file_name)
        if cis.empty:
            log("No CI data available for statistics calculation")
            return False
        
        # Calculate statistics
        stats = calculate_overall_statistics(config_file_name, cis)
        if not stats:
            log("Failed to calculate statistics")
            return False
        
        # Save to JSON file
        statistics_file_path = os.path.join(os.path.dirname(__file__), 'data', 'statistics.json')
        with open(statistics_file_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        log(f"Updated statistics file: {len(cis)} CIs, {stats['total_recording_minutes']:.1f} minutes recording duration")
        return True
        
    except Exception as e:
        log(f"Error updating statistics file: {e}")
        return False

def main():
    # Initialize logger first
    setup_logger()
    
    log("=== CRON JOB STARTING ===")
    log("Starting main function...")
    log("Logging initialized - logs will be written to data/cron.log with daily rotation")
    
    # Load core configurations with error handling
    try:
        core_config = load_core_config()
    except Exception as e:
        log(f"FATAL ERROR loading core configuration: {e}")
        return
    
    # Get configurations from YAML with validation
    try:
        config_file_name = core_config.get('file_name')
        config_url = core_config.get('url')
        config_home_url = core_config.get('home_url')
        config_notifications_file = core_config.get('notifications_config_file')
        
        # Get cron intervals with defaults and validation
        cron_intervals = core_config.get('cron_intervals', {})
        ci_list_update_interval = cron_intervals.get('ci_list_update_interval', 288)      # Default: every 24 hours
        
        # Validate interval values
        if not isinstance(ci_list_update_interval, int) or ci_list_update_interval < 1:
            log(f"WARNING: Invalid ci_list_update_interval: {ci_list_update_interval}, using default: 288")
            ci_list_update_interval = 288
            
    except Exception as e:
        log(f"ERROR processing configuration: {e}")
        return
    
    log(f"Configuration values:")
    log(f"  file_name: {config_file_name}")
    log(f"  url: {config_url}")
    log(f"  home_url: {config_home_url}")
    log(f"  notifications_file: {config_notifications_file}")
    log(f"  ci_list_update_interval: {ci_list_update_interval} iterations ({ci_list_update_interval * 5} minutes)")
    
    if not config_file_name or not config_url:
        log("ERROR: Required configuration missing in config.yaml")
        log(f"  file_name: {config_file_name}")
        log(f"  url: {config_url}")
        return
    
    log(f"Configuration validation passed")
    log(f"Using file: {config_file_name}")
    log(f"Using URL: {config_url}")
    
    # Main loop - run every 5 minutes with comprehensive error handling
    iteration_count = 0
    consecutive_errors = 0
    max_consecutive_errors = 10  # Stop after 10 consecutive errors
    
    log("Entering main loop...")
    last_stats_update_time = 0  # epoch seconds; controls hourly stats updates
    while True:
        try:
            iteration_count += 1
            log(f"=== ITERATION {iteration_count} ===")
            log(f"Running cron job at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Reset error counter on successful iteration
            consecutive_errors = 0
            
            # Initialize data file with error handling
            try:
                log("Calling initialize_data_file...")
                initialize_data_file(config_file_name)
                log("initialize_data_file completed")
            except Exception as e:
                log(f"ERROR in initialize_data_file: {e}")
                # Continue with next step even if initialization fails
            
            # Update file with error handling
            try:
                log("Calling update_file...")
                update_file(config_file_name, config_url)
                log("update_file completed")
            except Exception as e:
                log(f"ERROR in update_file: {e}")
                # Continue with other tasks even if update_file fails
            
            # Update CI list file at configured interval with error handling
            if iteration_count % ci_list_update_interval == 0:
                try:
                    log(f"CI list update (every {ci_list_update_interval} iterations = {ci_list_update_interval * 5} minutes)...")
                    ci_list_file_path = os.path.join(os.path.dirname(__file__), 'data', 'ci_list.json')
                    update_ci_list_file(config_file_name, ci_list_file_path)
                    log("CI list update completed")
                except Exception as e:
                    log(f"ERROR in CI list update: {e}")
            
            # Update statistics file hourly (time-based) with error handling
            now_epoch = time.time()
            if now_epoch - last_stats_update_time >= 3600:
                try:
                    log("Updating statistics file (hourly)...")
                    update_statistics_file(config_file_name)
                    last_stats_update_time = now_epoch
                    log("Statistics update completed")
                except Exception as e:
                    log(f"ERROR in statistics update: {e}")
            

            
            # Check if notifications are enabled with comprehensive error handling
            try:
                log("Checking notifications...")
                if config_notifications_file and os.path.exists(config_notifications_file):
                    log(f"Notifications file exists: {config_notifications_file}")
                    try:
                        with open(config_notifications_file, 'r') as f:
                            notifications_config = yaml.safe_load(f)
                        log(f"Notifications config loaded: {len(notifications_config) if notifications_config else 0} profiles")
                        # notifications_config is a list, so we check if it's not empty instead of looking for 'enabled'
                        if notifications_config and len(notifications_config) > 0:
                            log("Sending notifications...")
                            send_apprise_notifications(config_file_name, config_notifications_file, config_home_url)
                            log("Notifications sent successfully")
                        else:
                            log("No notification profiles found")
                    except Exception as e:
                        log(f"ERROR with notifications: {e}")
                else:
                    log(f"Notifications file not found or not specified: {config_notifications_file}")
            except Exception as e:
                log(f"ERROR checking notifications: {e}")
            
            log(f"Cron job completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Force garbage collection every 10 iterations to prevent memory buildup
            if iteration_count % 10 == 0:
                try:
                    log("Performing garbage collection...")
                    gc.collect()
                    log("Garbage collection completed")
                except Exception as e:
                    log(f"ERROR in garbage collection: {e}")
            
            # Clean up old log files every 288 iterations (24 hours)
            if iteration_count % 288 == 0:
                try:
                    log("Cleaning up old log files...")
                    cleanup_old_logs()
                    log("Log cleanup completed")
                except Exception as e:
                    log(f"ERROR in log cleanup: {e}")
            
            log("Sleeping for 5 minutes...")
            
            # Sleep for 5 minutes (300 seconds) with error handling
            try:
                time.sleep(300)
            except Exception as e:
                log(f"ERROR during sleep: {e}")
                # Continue anyway
            
        except KeyboardInterrupt:
            log("Cron job interrupted, exiting...")
            break
        except Exception as e:
            consecutive_errors += 1
            log(f"ERROR in cron job (error #{consecutive_errors}): {e}")
            log(f"Exception type: {type(e).__name__}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            
            # Check if we've had too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                log(f"FATAL: Too many consecutive errors ({consecutive_errors}), stopping cron job")
                break
            
            # Sleep for 5 minutes before retry with error handling
            try:
                log("Sleeping for 5 minutes before retry...")
                time.sleep(300)
            except Exception as sleep_error:
                log(f"ERROR during error recovery sleep: {sleep_error}")
                # If we can't even sleep, we should probably exit
                log("Cannot recover from error, exiting...")
                break

if __name__ == '__main__':
    try:
        # Initialize logger first
        setup_logger()
        log("Script started - __name__ == '__main__'")
        main()
    except KeyboardInterrupt:
        log("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        try:
            log(f"FATAL ERROR in main: {e}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
        except:
            # If even logging fails, just print to stderr
            print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)
else:
    try:
        # Initialize logger for imports too
        setup_logger()
        log(f"Script imported - __name__ == '{__name__}'")
    except:
        # If logging fails during import, just continue
        pass

def cleanup_old_logs():
    """Clean up old log files (older than 7 days)"""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(data_dir):
            return
        
        current_time = time.time()
        cutoff_time = current_time - (7 * 24 * 60 * 60)  # 7 days ago
        
        for filename in os.listdir(data_dir):
            if filename.startswith('cron.log.') and filename.endswith(('.log', '.gz')):
                file_path = os.path.join(data_dir, filename)
                try:
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        log(f"Cleaned up old log file: {filename}")
                except Exception as e:
                    log(f"Error cleaning up log file {filename}: {e}")
                    
    except Exception as e:
        log(f"Error in cleanup_old_logs: {e}")

def compute_incident_and_availability_metrics(config_file_name):
    """
    Compute per-CI and aggregated availability metrics using availability time series in HDF5.
    - Treat each timestamp's value (0/1) as status until the next timestamp (right-open interval).
    - For the last timestamp, extend interval to 'now'.
    - Incidents are 1->0 transitions; repair is 0->1.
    Returns dict with rollups and per_ci details.
    """
    metrics = {
        'overall_uptime_minutes': 0.0,
        'overall_downtime_minutes': 0.0,
        'overall_availability_percentage_rollup': 0.0,
        'total_incidents': 0,
        'mttr_minutes_mean': 0.0,
        'mtbf_minutes_mean': 0.0,
        'top_unstable_cis_by_incidents': [],
        'top_downtime_cis': [],
        'per_ci_metrics': {}
    }
    try:
        if not os.path.exists(config_file_name):
            return metrics
        now_epoch = time.time()
        with h5py.File(config_file_name, 'r', swmr=True) as f:
            if 'availability' not in f:
                return metrics
            availability_group = f['availability']
            # Enrich CI metadata (name, organization) from general CI data
            ci_metadata = {}
            try:
                cis_df = get_data_of_all_cis(config_file_name)
                if not cis_df.empty and all(c in cis_df.columns for c in ['ci','name','organization']):
                    for _, row in cis_df[['ci','name','organization']].iterrows():
                        ci_metadata[str(row['ci'])] = {
                            'name': str(row['name']) if not pd.isna(row['name']) else '',
                            'organization': str(row['organization']) if not pd.isna(row['organization']) else ''
                        }
            except Exception as e:
                log(f"Warning: could not enrich CI metadata: {e}")
            per_ci_results = {}
            total_downtime_list = []
            total_mttr_values = []
            total_mtbf_values = []
            total_incidents = 0
            overall_uptime = 0.0
            overall_downtime = 0.0
            for ci_name in availability_group.keys():
                ci_group = availability_group[ci_name]
                # Collect and sort all timestamps as floats
                ts_list = []
                for k in ci_group.keys():
                    try:
                        ts_list.append(float(k))
                    except Exception:
                        continue
                if not ts_list:
                    continue
                ts_list.sort()
                # Build status sequence aligned to ts_list
                statuses = []
                for ts in ts_list:
                    try:
                        ds = ci_group[str(ts)]
                        val = int(ds[()]) if isinstance(ds, h5py.Dataset) else int(ds)
                        statuses.append(1 if val != 0 else 0)
                    except Exception:
                        statuses.append(0)
                # Compute intervals
                downtime_minutes = 0.0
                uptime_minutes = 0.0
                incidents = 0
                mttr_list = []
                mtbf_list = []
                current_state = statuses[0]
                last_change_epoch = ts_list[0]
                last_epoch = ts_list[0]
                # Track last up-period start for MTBF (time between incidents)
                last_repair_epoch = None
                for idx in range(len(ts_list) - 1):
                    start = ts_list[idx]
                    end = ts_list[idx + 1]
                    dur_min = (end - start) / 60.0
                    if statuses[idx] == 1:
                        uptime_minutes += dur_min
                    else:
                        downtime_minutes += dur_min
                    # Transition detection at idx+1 (state applies from ts_list[idx])
                    if statuses[idx + 1] != statuses[idx]:
                        # state changes at 'end'
                        prev_state = statuses[idx]
                        new_state = statuses[idx + 1]
                        if prev_state == 1 and new_state == 0:
                            incidents += 1
                            last_change_epoch = end
                            # end of an up period -> start of downtime; close MTBF if there was a prior repair
                            if last_repair_epoch is not None:
                                mtbf_list.append((end - last_repair_epoch) / 60.0)
                        elif prev_state == 0 and new_state == 1:
                            # repair completed: downtime from last_change to end
                            if last_change_epoch is not None:
                                mttr_list.append((end - last_change_epoch) / 60.0)
                            last_repair_epoch = end
                        current_state = new_state
                    last_epoch = end
                # Extend last interval to now
                if last_epoch < now_epoch:
                    tail_min = (now_epoch - last_epoch) / 60.0
                    if statuses[-1] == 1:
                        uptime_minutes += tail_min
                    else:
                        downtime_minutes += tail_min
                # If last state is down, we have an open incident; do not close MTTR until repair occurs
                availability_pct = (uptime_minutes / (uptime_minutes + downtime_minutes) * 100.0) if (uptime_minutes + downtime_minutes) > 0 else 0.0
                meta = ci_metadata.get(ci_name, {})
                ci_result = {
                    'incidents': int(incidents),
                    'uptime_minutes': float(uptime_minutes),
                    'downtime_minutes': float(downtime_minutes),
                    'availability_percentage': float(availability_pct),
                    'mttr_minutes_mean': float(np.mean(mttr_list)) if mttr_list else 0.0,
                    'mtbf_minutes_mean': float(np.mean(mtbf_list)) if mtbf_list else 0.0,
                    'longest_outage_minutes': float(max(mttr_list)) if mttr_list else ( (now_epoch - last_change_epoch) / 60.0 if statuses[-1] == 0 else 0.0 ),
                    'name': meta.get('name', ''),
                    'organization': meta.get('organization', '')
                }
                per_ci_results[ci_name] = ci_result
                total_incidents += incidents
                overall_uptime += uptime_minutes
                overall_downtime += downtime_minutes
                total_downtime_list.append((ci_name, downtime_minutes))
                if mttr_list:
                    total_mttr_values.extend(mttr_list)
                if mtbf_list:
                    total_mtbf_values.extend(mtbf_list)
            overall_pct = (overall_uptime / (overall_uptime + overall_downtime) * 100.0) if (overall_uptime + overall_downtime) > 0 else 0.0
            # Rankings
            top_unstable = sorted(((ci, per_ci_results[ci]['incidents']) for ci in per_ci_results), key=lambda x: x[1], reverse=True)[:10]
            top_downtime = sorted(total_downtime_list, key=lambda x: x[1], reverse=True)[:10]
            metrics.update({
                'overall_uptime_minutes': overall_uptime,
                'overall_downtime_minutes': overall_downtime,
                'overall_availability_percentage_rollup': overall_pct,
                'total_incidents': total_incidents,
                'mttr_minutes_mean': float(np.mean(total_mttr_values)) if total_mttr_values else 0.0,
                'mtbf_minutes_mean': float(np.mean(total_mtbf_values)) if total_mtbf_values else 0.0,
                'top_unstable_cis_by_incidents': [{'ci': ci, 'incidents': inc} for ci, inc in top_unstable],
                'top_downtime_cis': [{'ci': ci, 'downtime_minutes': mins} for ci, mins in top_downtime],
                'per_ci_metrics': per_ci_results
            })
    except Exception as e:
        log(f"Error computing availability metrics: {e}")
    return metrics