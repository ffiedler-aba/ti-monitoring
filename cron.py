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

# Enhanced logging setup with file logging and daily rotation
import logging
from logging.handlers import TimedRotatingFileHandler
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
        
        # Create formatter
        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
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

def format_duration(hours):
    """Format duration in a human-readable way with error handling"""
    try:
        if not isinstance(hours, (int, float)) or hours < 0:
            log(f"Warning: Invalid hours value: {hours}")
            return "Unbekannt"
            
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes} Minuten"
        elif hours < 24:
            return f"{hours:.1f} Stunden"
        else:
            days = hours / 24
            return f"{days:.1f} Tage"
    except Exception as e:
        log(f"ERROR in format_duration: {e}")
        return "Unbekannt"

def calculate_overall_statistics(config_file_name, cis):
    """
    Calculate overall statistics for all Configuration Items including:
    - Total counts and current availability
    - Overall availability percentage
    - Recording time range
    - Product distribution
    - Organization distribution
    """
    try:
        if cis.empty:
            log("Warning: Empty CIS DataFrame provided to calculate_overall_statistics")
            return {}
        
        # Basic counts with error handling
        try:
            total_cis = len(cis)
            if total_cis == 0:
                log("Warning: No CIs found in DataFrame")
                return {}
        except Exception as e:
            log(f"Error calculating total CIs: {e}")
            return {}
        
        # Current availability with error handling
        try:
            if 'current_availability' not in cis.columns:
                log("Warning: 'current_availability' column not found")
                currently_available = 0
                currently_unavailable = total_cis
            else:
                currently_available = int(cis['current_availability'].sum())
                currently_unavailable = total_cis - currently_available
            overall_availability_percentage = (currently_available / total_cis) * 100 if total_cis > 0 else 0
        except Exception as e:
            log(f"Error calculating availability: {e}")
            currently_available = 0
            currently_unavailable = total_cis
            overall_availability_percentage = 0
        
        # Product distribution with error handling
        try:
            if 'product' not in cis.columns:
                log("Warning: 'product' column not found")
                product_counts = pd.Series()
                total_products = 0
            else:
                product_counts = cis['product'].value_counts()
                total_products = len(product_counts)
        except Exception as e:
            log(f"Error calculating product distribution: {e}")
            product_counts = pd.Series()
            total_products = 0
        
        # Organization distribution with error handling
        try:
            if 'organization' not in cis.columns:
                log("Warning: 'organization' column not found")
                organization_counts = pd.Series()
                total_organizations = 0
            else:
                organization_counts = cis['organization'].value_counts()
                total_organizations = len(organization_counts)
        except Exception as e:
            log(f"Error calculating organization distribution: {e}")
            organization_counts = pd.Series()
            total_organizations = 0
        
        # Current status distribution with error handling
        try:
            if 'current_availability' not in cis.columns:
                available_count = 0
                unavailable_count = total_cis
            else:
                status_counts = cis['current_availability'].value_counts()
                available_count = int(status_counts.get(1, 0))
                unavailable_count = int(status_counts.get(0, 0))
        except Exception as e:
            log(f"Error calculating status distribution: {e}")
            available_count = 0
            unavailable_count = total_cis
        
        # Recent changes with error handling
        try:
            if 'availability_difference' not in cis.columns:
                log("Warning: 'availability_difference' column not found")
                changes_count = 0
            else:
                recent_changes = cis[cis['availability_difference'] != 0]
                changes_count = len(recent_changes)
        except Exception as e:
            log(f"Error calculating recent changes: {e}")
            changes_count = 0
        
        # Get overall recording time range with comprehensive error handling
        latest_timestamp = None
        earliest_timestamp = None
        data_age_formatted = "Unbekannt"
        
        try:
            if 'time' in cis.columns and not cis['time'].isna().all():
                # Get timestamps with error handling
                try:
                    latest_timestamp = pd.to_datetime(cis['time'].max())
                    earliest_timestamp = pd.to_datetime(cis['time'].min())
                except Exception as e:
                    log(f"Error parsing timestamps: {e}")
                    latest_timestamp = None
                    earliest_timestamp = None
                
                # Timezone handling with error handling
                if latest_timestamp is not None and earliest_timestamp is not None:
                    try:
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
                    except Exception as e:
                        log(f"Error handling timezone conversion: {e}")
                        latest_timestamp = None
                        earliest_timestamp = None
                        data_age_formatted = "Unbekannt"
            else:
                log("Warning: 'time' column not found or all values are NaN")
        except Exception as e:
            log(f"Error processing time data: {e}")
            latest_timestamp = None
            earliest_timestamp = None
            data_age_formatted = "Unbekannt"
    
        # Calculate total recording time from the overall time range (more accurate)
        try:
            if latest_timestamp and earliest_timestamp and latest_timestamp != earliest_timestamp:
                total_recording_minutes = (latest_timestamp - earliest_timestamp).total_seconds() / 60
                log(f"Total recording time: {earliest_timestamp} to {latest_timestamp} = {total_recording_minutes:.1f} minutes")
            else:
                # Fallback: estimate from current time - earliest timestamp if available
                if earliest_timestamp:
                    current_time = pd.Timestamp.now(tz=pytz.timezone('Europe/Berlin'))
                    total_recording_minutes = (current_time - earliest_timestamp).total_seconds() / 60
                    log(f"Total recording time estimated from earliest timestamp: {total_recording_minutes:.1f} minutes")
                else:
                    # Last resort: use a reasonable default (e.g., 2 days)
                    total_recording_minutes = 2 * 24 * 60  # 2 days in minutes
                    log(f"Total recording time using default (2 days): {total_recording_minutes:.1f} minutes")
        except Exception as e:
            log(f"Error calculating total recording time: {e}")
            total_recording_minutes = 2 * 24 * 60  # Default to 2 days
            
    except Exception as e:
        log(f"Warning: Could not calculate comprehensive statistics: {e}")
        # Set default values if calculation fails
        total_recording_minutes = 0
    
        # Return results with comprehensive error handling
        try:
            return {
                'total_cis': int(total_cis),
                'currently_available': int(currently_available),
                'currently_unavailable': int(currently_unavailable),
                'overall_availability_percentage': float(overall_availability_percentage),
                'total_products': int(total_products),
                'total_organizations': int(total_organizations),
                'available_count': int(available_count),
                'unavailable_count': int(unavailable_count),
                'changes_count': int(changes_count),
                'latest_timestamp': latest_timestamp.isoformat() if latest_timestamp else None,
                'earliest_timestamp': earliest_timestamp.isoformat() if earliest_timestamp else None,
                'data_age_formatted': data_age_formatted,
                'product_counts': product_counts.to_dict() if hasattr(product_counts, 'to_dict') else {},
                'organization_counts': organization_counts.to_dict() if hasattr(organization_counts, 'to_dict') else {},
                'total_recording_minutes': float(total_recording_minutes),
                'calculated_at': time.time()
            }
        except Exception as e:
            log(f"Error creating return dictionary: {e}")
            # Return minimal safe values
            return {
                'total_cis': 0,
                'currently_available': 0,
                'currently_unavailable': 0,
                'overall_availability_percentage': 0.0,
                'total_products': 0,
                'total_organizations': 0,
                'available_count': 0,
                'unavailable_count': 0,
                'changes_count': 0,
                'latest_timestamp': None,
                'earliest_timestamp': None,
                'data_age_formatted': "Unbekannt",
                'product_counts': {},
                'organization_counts': {},
                'total_recording_minutes': 0.0,
                'calculated_at': time.time()
            }
    
    except Exception as e:
        log(f"FATAL ERROR in calculate_overall_statistics: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        # Return empty dict to prevent further errors
        return {}

def update_statistics_file(config_file_name, statistics_file_path):
    """Update the statistics file with current overall statistics"""
    try:
        log(f"Updating statistics file: {statistics_file_path}")
        
        # Validate inputs
        if not config_file_name:
            log("ERROR: config_file_name is empty or None")
            return False
            
        if not statistics_file_path:
            log("ERROR: statistics_file_path is empty or None")
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
            log("No CIs found in data file for statistics calculation")
            return False
        
        # Calculate overall statistics with error handling
        try:
            stats = calculate_overall_statistics(config_file_name, cis_df)
        except Exception as e:
            log(f"ERROR calculating statistics: {e}")
            return False
        
        if not stats:
            log("ERROR: Statistics calculation returned empty result")
            return False
        
        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(statistics_file_path), exist_ok=True)
        except Exception as e:
            log(f"ERROR creating statistics directory: {e}")
            return False
        
        # Write to JSON file with comprehensive error handling
        try:
            # Create backup of existing file if it exists
            if os.path.exists(statistics_file_path):
                backup_path = statistics_file_path + '.backup'
                try:
                    import shutil
                    shutil.copy2(statistics_file_path, backup_path)
                    log(f"Created backup: {backup_path}")
                except Exception as e:
                    log(f"Warning: Could not create backup: {e}")
            
            # Write new statistics file
            with open(statistics_file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            # Verify the file was written correctly
            if os.path.exists(statistics_file_path) and os.path.getsize(statistics_file_path) > 0:
                log(f"Statistics file updated successfully with {stats.get('total_cis', 0)} CIs")
                return True
            else:
                log("ERROR: Statistics file was not written correctly")
                return False
                
        except Exception as e:
            log(f"ERROR writing statistics file: {e}")
            # Try to restore backup if it exists
            backup_path = statistics_file_path + '.backup'
            if os.path.exists(backup_path):
                try:
                    import shutil
                    shutil.copy2(backup_path, statistics_file_path)
                    log(f"Restored backup file: {backup_path}")
                except Exception as e:
                    log(f"ERROR restoring backup: {e}")
            return False
            
    except Exception as e:
        log(f"FATAL ERROR in update_statistics_file: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
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
        statistics_update_interval = cron_intervals.get('statistics_update_interval', 2)  # Default: every 10 minutes
        ci_list_update_interval = cron_intervals.get('ci_list_update_interval', 288)      # Default: every 24 hours
        
        # Validate interval values
        if not isinstance(statistics_update_interval, int) or statistics_update_interval < 1:
            log(f"WARNING: Invalid statistics_update_interval: {statistics_update_interval}, using default: 2")
            statistics_update_interval = 2
            
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
    log(f"  statistics_update_interval: {statistics_update_interval} iterations ({statistics_update_interval * 5} minutes)")
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
            
            # Update statistics file at configured interval with error handling
            if iteration_count % statistics_update_interval == 0:
                try:
                    log(f"Statistics update (every {statistics_update_interval} iterations = {statistics_update_interval * 5} minutes)...")
                    statistics_file_path = os.path.join(os.path.dirname(__file__), 'data', 'statistics.json')
                    success = update_statistics_file(config_file_name, statistics_file_path)
                    if success:
                        log("Statistics update completed")
                    else:
                        log("Statistics update failed")
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