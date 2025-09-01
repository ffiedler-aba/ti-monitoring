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

# Enhanced logging setup
def log(message):
    """Enhanced logging function with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()  # Force output to be displayed immediately

def load_config():
    """Load configuration from YAML file"""
    log("Starting configuration loading...")
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    log(f"Config path: {config_path}")
    log(f"Current working directory: {os.getcwd()}")
    log(f"Config file exists: {os.path.exists(config_path)}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        log(f"Configuration loaded successfully. Keys: {list(config.keys())}")
        return config
    except FileNotFoundError as e:
        log(f"ERROR: Config file not found: {e}")
        return {}
    except Exception as e:
        log(f"ERROR: Failed to load config: {e}")
        return {}

def load_core_config():
    """Load core configuration from YAML file"""
    log("Loading core configuration...")
    config = load_config()
    core_config = config.get('core', {})
    log(f"Core config loaded. Keys: {list(core_config.keys())}")
    return core_config

def update_ci_list_file(config_file_name, ci_list_file_path):
    """Update the CI list file with current configuration items"""
    try:
        log(f"Updating CI list file: {ci_list_file_path}")
        
        # Get all CIs from the data file
        cis_df = get_data_of_all_cis(config_file_name)
        
        if not cis_df.empty:
            # Convert to list of dictionaries with relevant information
            ci_list = []
            for _, row in cis_df.iterrows():
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
            
            # Write to JSON file
            with open(ci_list_file_path, 'w', encoding='utf-8') as f:
                json.dump(ci_list, f, ensure_ascii=False, indent=2)
            
            log(f"CI list file updated successfully with {len(ci_list)} CIs")
            return True
        else:
            log("No CIs found in data file")
            return False
            
    except Exception as e:
        log(f"ERROR updating CI list file: {e}")
        return False

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
        log(f"Total recording time: {earliest_timestamp} to {latest_timestamp} = {total_recording_minutes:.1f} minutes")
    else:
        total_recording_minutes = 0
    
    try:
        # Take a sample of CIs to calculate downtime (max 20 CIs to avoid performance issues)
        sample_size = min(20, len(cis))
        if sample_size > 0:
            # Take a representative sample
            sample_cis = cis.sample(n=sample_size, random_state=42)  # Fixed seed for consistency
            
            log(f"Calculating downtime statistics for sample of {sample_size} CIs out of {len(cis)} total")
            
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
                    log(f"Warning: Could not calculate downtime for CI {ci_id}: {e}")
                    continue
            
            # Scale up the downtime/uptime results to estimate total across all CIs
            if sample_size > 0:
                scale_factor = len(cis) / sample_size
                total_downtime_minutes *= scale_factor
                total_uptime_minutes *= scale_factor
                
                log(f"Scaled downtime/uptime by factor {scale_factor:.2f} to estimate totals")
        
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
        log(f"Warning: Could not calculate comprehensive downtime statistics: {e}")
        # Set default values if calculation fails
        total_downtime_minutes = total_downtime_hours = total_downtime_days = 0
        total_downtime_weeks = total_downtime_years = 0
        total_uptime_minutes = total_uptime_hours = total_uptime_days = 0
        overall_availability_percentage_total = overall_availability_percentage
        downtime_per_day = downtime_per_week = downtime_per_year = 0
    
    return {
        'total_cis': int(total_cis),
        'currently_available': int(currently_available),
        'currently_unavailable': int(currently_unavailable),
        'overall_availability_percentage': float(overall_availability_percentage),
        'overall_availability_percentage_total': float(overall_availability_percentage_total),
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
        'total_downtime_minutes': float(total_downtime_minutes),
        'total_downtime_hours': float(total_downtime_hours),
        'total_downtime_days': float(total_downtime_days),
        'total_downtime_weeks': float(total_downtime_weeks),
        'total_downtime_years': float(total_downtime_years),
        'total_uptime_minutes': float(total_uptime_minutes),
        'total_uptime_hours': float(total_uptime_hours),
        'total_uptime_days': float(total_uptime_days),
        'total_recording_minutes': float(total_recording_minutes),
        'downtime_per_day': float(downtime_per_day),
        'downtime_per_week': float(downtime_per_week),
        'downtime_per_year': float(downtime_per_year),
        'calculated_at': time.time()
    }

def update_statistics_file(config_file_name, statistics_file_path):
    """Update the statistics file with current overall statistics"""
    try:
        log(f"Updating statistics file: {statistics_file_path}")
        
        # Get all CIs from the data file
        cis_df = get_data_of_all_cis(config_file_name)
        
        if not cis_df.empty:
            # Calculate overall statistics
            stats = calculate_overall_statistics(config_file_name, cis_df)
            
            # Write to JSON file
            with open(statistics_file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            log(f"Statistics file updated successfully with {stats.get('total_cis', 0)} CIs")
            return True
        else:
            log("No CIs found in data file for statistics calculation")
            return False
            
    except Exception as e:
        log(f"ERROR updating statistics file: {e}")
        return False

def main():
    log("=== CRON JOB STARTING ===")
    log("Starting main function...")
    
    # Load core configurations
    core_config = load_core_config()
    
    # Get configurations from YAML
    config_file_name = core_config.get('file_name')
    config_url = core_config.get('url')
    config_home_url = core_config.get('home_url')
    config_notifications_file = core_config.get('notifications_config_file')
    
    # Get cron intervals with defaults
    cron_intervals = core_config.get('cron_intervals', {})
    statistics_update_interval = cron_intervals.get('statistics_update_interval', 2)  # Default: every 10 minutes
    ci_list_update_interval = cron_intervals.get('ci_list_update_interval', 288)      # Default: every 24 hours
    
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
    
    # Main loop - run every 5 minutes
    iteration_count = 0
    log("Entering main loop...")
    while True:
        try:
            iteration_count += 1
            log(f"=== ITERATION {iteration_count} ===")
            log(f"Running cron job at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            log("Calling initialize_data_file...")
            initialize_data_file(config_file_name)
            log("initialize_data_file completed")
            
            log("Calling update_file...")
            update_file(config_file_name, config_url)
            log("update_file completed")
            
            # Update CI list file at configured interval
            if iteration_count % ci_list_update_interval == 0:
                log(f"CI list update (every {ci_list_update_interval} iterations = {ci_list_update_interval * 5} minutes)...")
                ci_list_file_path = os.path.join(os.path.dirname(__file__), 'data', 'ci_list.json')
                update_ci_list_file(config_file_name, ci_list_file_path)
                log("CI list update completed")
            
            # Update statistics file at configured interval
            if iteration_count % statistics_update_interval == 0:
                log(f"Statistics update (every {statistics_update_interval} iterations = {statistics_update_interval * 5} minutes)...")
                statistics_file_path = os.path.join(os.path.dirname(__file__), 'data', 'statistics.json')
                update_statistics_file(config_file_name, statistics_file_path)
                log("Statistics update completed")
            
            # Check if notifications are enabled
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
            
            log(f"Cron job completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Force garbage collection every 10 iterations to prevent memory buildup
            if iteration_count % 10 == 0:
                log("Performing garbage collection...")
                gc.collect()
                log("Garbage collection completed")
            
            log("Sleeping for 5 minutes...")
            
            # Sleep for 5 minutes (300 seconds)
            time.sleep(300)
            
        except KeyboardInterrupt:
            log("Cron job interrupted, exiting...")
            break
        except Exception as e:
            log(f"ERROR in cron job: {e}")
            log(f"Exception type: {type(e).__name__}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            log("Sleeping for 5 minutes before retry...")
            time.sleep(300)

if __name__ == '__main__':
    log("Script started - __name__ == '__main__'")
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR in main: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
else:
    log(f"Script imported - __name__ == '{__name__}'")