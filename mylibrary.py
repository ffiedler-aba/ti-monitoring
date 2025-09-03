import os
import psycopg2
from psycopg2.extras import execute_values
import h5py
import pandas as pd
import yaml
from datetime import datetime, timezone
from typing import Optional

def load_config():
    """Load configuration from YAML file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        if not os.path.exists(config_path):
            return {}
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def get_db_conn():
    # Load database configuration from config.yaml
    config = load_config()
    tsdb_config = config.get('core', {}).get('timescaledb', {})
    
    host = tsdb_config.get('host', 'db')
    port = tsdb_config.get('port', 5432)
    db = tsdb_config.get('dbname', 'timonitor')
    user = tsdb_config.get('user', 'timonitor')
    pwd = tsdb_config.get('password', 'timonitor')
    
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)

def init_timescaledb_schema():
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE EXTENSION IF NOT EXISTS timescaledb;
            CREATE TABLE IF NOT EXISTS measurements (
              ci TEXT NOT NULL,
              ts TIMESTAMPTZ NOT NULL,
              status SMALLINT NOT NULL,
              PRIMARY KEY (ci, ts)
            );
            SELECT create_hypertable('measurements','ts', if_not_exists => TRUE);
            
            CREATE TABLE IF NOT EXISTS ci_metadata (
              ci TEXT PRIMARY KEY,
              name TEXT,
              organization TEXT,
              product TEXT,
              bu TEXT,
              tid TEXT,
              pdt TEXT,
              comment TEXT,
              updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        # Optional: continuous aggregates, retention policies can be added later

def write_measurements(rows):
    """rows: iterable of (ci, ts(datetime|str|epoch), status:int)"""
    if not rows:
        return 0
    with get_db_conn() as conn, conn.cursor() as cur:
        execute_values(cur,
            "INSERT INTO measurements (ci, ts, status) VALUES %s ON CONFLICT DO NOTHING",
            rows
        )
        return cur.rowcount

def update_ci_metadata(ci_data):
    """Aktualisiert CI-Metadaten in TimescaleDB."""
    if not ci_data:
        return 0
    with get_db_conn() as conn, conn.cursor() as cur:
        execute_values(cur,
            """INSERT INTO ci_metadata (ci, name, organization, product, bu, tid, pdt, comment) 
               VALUES %s 
               ON CONFLICT (ci) DO UPDATE SET 
                 name = EXCLUDED.name,
                 organization = EXCLUDED.organization,
                 product = EXCLUDED.product,
                 bu = EXCLUDED.bu,
                 tid = EXCLUDED.tid,
                 pdt = EXCLUDED.pdt,
                 comment = EXCLUDED.comment,
                 updated_at = NOW()""",
            ci_data
        )
        return cur.rowcount

def ingest_hdf5_to_timescaledb(hdf5_path: str, max_rows: Optional[int] = None) -> int:
    """Streamt availability aus HDF5 und schreibt idempotent nach TimescaleDB.
    max_rows: optionales Limit zur Drosselung pro Lauf.
    """
    if not os.path.exists(hdf5_path):
        return 0
    init_timescaledb_schema()
    inserted = 0
    batch = []
    batch_size = 5000
    processed = 0
    with get_db_conn() as conn, conn.cursor() as cur:
        with h5py.File(hdf5_path, 'r', swmr=True) as f:
            if 'availability' not in f:
                return 0
            availability = f['availability']
            for ci in availability.keys():
                ci_group = availability[ci]
                for ts_key in ci_group.keys():
                    try:
                        ts = float(ts_key)
                        ds = ci_group[ts_key]
                        val = int(ds[()]) if isinstance(ds, h5py.Dataset) else int(ds)
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        batch.append((ci, dt, val))
                        processed += 1
                        if len(batch) >= batch_size:
                            cur.executemany(
                                "INSERT INTO measurements (ci, ts, status) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                                batch,
                            )
                            inserted += cur.rowcount
                            batch.clear()
                        if max_rows is not None and processed >= max_rows:
                            break
                    except Exception:
                        continue
                if max_rows is not None and processed >= max_rows:
                    break
            if batch:
                cur.executemany(
                    "INSERT INTO measurements (ci, ts, status) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    batch,
                )
                inserted += cur.rowcount
                batch.clear()
    return inserted

def setup_timescaledb_retention(keep_days: int = 185) -> None:
    """Setzt eine Retention-Policy (drop_chunks) auf measurements; idempotent."""
    with get_db_conn() as conn, conn.cursor() as cur:
        # add_retention_policy ist idempotent mit if_not_exists => TRUE
        sql = f"SELECT add_retention_policy('measurements', INTERVAL '{int(keep_days)} days', if_not_exists => TRUE);"
        cur.execute(sql)

def get_timescaledb_ci_data() -> pd.DataFrame:
    """Lädt CI-Daten aus TimescaleDB für Statistiken."""
    with get_db_conn() as conn:
        # Lade alle CIs mit ihren aktuellen Status und Metadaten
        query = """
        WITH latest_status AS (
            SELECT DISTINCT ON (ci) 
                ci, 
                ts, 
                status,
                LAG(status) OVER (PARTITION BY ci ORDER BY ts) as prev_status
            FROM measurements 
            ORDER BY ci, ts DESC
        ),
        ci_metadata AS (
            SELECT 
                ci,
                name,
                organization,
                product,
                bu,
                tid,
                pdt,
                comment
            FROM ci_metadata
        )
        SELECT 
            ls.ci,
            ls.status as current_availability,
            ls.ts as time,
            COALESCE(cm.name, '') as name,
            COALESCE(cm.organization, '') as organization,
            COALESCE(cm.product, '') as product,
            COALESCE(cm.bu, '') as bu,
            COALESCE(cm.tid, '') as tid,
            COALESCE(cm.pdt, '') as pdt,
            COALESCE(cm.comment, '') as comment,
            CASE 
                WHEN ls.status = 1 AND ls.prev_status = 0 THEN 1 
                ELSE 0 
            END as availability_difference
        FROM latest_status ls
        LEFT JOIN ci_metadata cm ON ls.ci = cm.ci
        ORDER BY ls.ci
        """
        return pd.read_sql_query(query, conn)

def get_timescaledb_statistics_data() -> dict:
    """Lädt erweiterte Statistiken aus TimescaleDB."""
    with get_db_conn() as conn:
        # Gesamtstatistiken mit korrekter Zeitberechnung
        stats_query = """
        WITH time_bounds AS (
            SELECT 
                MIN(ts) as earliest_ts,
                MAX(ts) as latest_ts,
                COUNT(*) as total_datapoints,
                EXTRACT(EPOCH FROM (MAX(ts) - MIN(ts))) / 60.0 as total_recording_minutes
            FROM measurements
        ),
        ci_time_stats AS (
            SELECT 
                ci,
                COUNT(*) as datapoints,
                MIN(ts) as first_seen,
                MAX(ts) as last_seen,
                -- Vereinfachte Berechnung: 5 Minuten pro Datensatz
                SUM(CASE WHEN status = 1 THEN 5.0 ELSE 0 END) as uptime_minutes,
                SUM(CASE WHEN status = 0 THEN 5.0 ELSE 0 END) as downtime_minutes
            FROM measurements
            GROUP BY ci
        ),
        incident_stats AS (
            SELECT 
                ci,
                COUNT(*) as incidents
            FROM (
                SELECT 
                    ci,
                    status,
                    LAG(status) OVER (PARTITION BY ci ORDER BY ts) as prev_status
                FROM measurements
            ) t
            WHERE status = 0 AND prev_status = 1
            GROUP BY ci
        )
        SELECT 
            (SELECT COUNT(DISTINCT ci) FROM measurements) as total_cis,
            (SELECT COUNT(DISTINCT ci) FROM measurements m1 
             WHERE m1.ci IN (
                 SELECT ci FROM measurements m2 
                 WHERE m2.ts = (SELECT MAX(ts) FROM measurements m3 WHERE m3.ci = m2.ci)
                 AND m2.status = 1
             )) as currently_available,
            (SELECT total_datapoints FROM time_bounds) as total_datapoints,
            (SELECT total_recording_minutes FROM time_bounds) as total_recording_minutes,
            (SELECT earliest_ts FROM time_bounds) as earliest_timestamp,
            (SELECT latest_ts FROM time_bounds) as latest_timestamp,
            (SELECT SUM(uptime_minutes) FROM ci_time_stats) as overall_uptime_minutes,
            (SELECT SUM(downtime_minutes) FROM ci_time_stats) as overall_downtime_minutes,
            (SELECT SUM(incidents) FROM incident_stats) as total_incidents
        """
        
        stats_result = pd.read_sql_query(stats_query, conn).iloc[0]
        
        # CI-spezifische Metriken mit korrekter Zeitberechnung
        ci_metrics_query = """
        WITH         ci_time_stats AS (
            SELECT 
                ci,
                COUNT(*) as datapoints,
                MIN(ts) as first_seen,
                MAX(ts) as last_seen,
                -- Vereinfachte Berechnung: 5 Minuten pro Datensatz
                SUM(CASE WHEN status = 1 THEN 5.0 ELSE 0 END) as uptime_minutes,
                SUM(CASE WHEN status = 0 THEN 5.0 ELSE 0 END) as downtime_minutes
            FROM measurements
            GROUP BY ci
        ),
        incident_metrics AS (
            SELECT 
                ci,
                COUNT(*) as incidents
            FROM (
                SELECT 
                    ci,
                    status,
                    LAG(status) OVER (PARTITION BY ci ORDER BY ts) as prev_status
                FROM measurements
            ) t
            WHERE status = 0 AND prev_status = 1
            GROUP BY ci
        )
        SELECT 
            cts.ci,
            cts.datapoints,
            cts.uptime_minutes,
            cts.downtime_minutes,
            cts.first_seen,
            cts.last_seen,
            COALESCE(im.incidents, 0) as incidents,
            CASE 
                WHEN (cts.uptime_minutes + cts.downtime_minutes) > 0 THEN 
                    (cts.uptime_minutes / (cts.uptime_minutes + cts.downtime_minutes)) * 100
                ELSE 100.0
            END as availability_percentage
        FROM ci_time_stats cts
        LEFT JOIN incident_metrics im ON cts.ci = im.ci
        ORDER BY COALESCE(im.incidents, 0) DESC, availability_percentage ASC
        LIMIT 10
        """
        
        ci_metrics = pd.read_sql_query(ci_metrics_query, conn)
        
        # Berechne Gesamtverfügbarkeit
        overall_uptime = float(stats_result['overall_uptime_minutes']) if stats_result['overall_uptime_minutes'] is not None else 0
        overall_downtime = float(stats_result['overall_downtime_minutes']) if stats_result['overall_downtime_minutes'] is not None else 0
        total_time = overall_uptime + overall_downtime
        overall_availability = (overall_uptime / total_time * 100) if total_time > 0 else 100.0
        
        return {
            'total_cis': int(stats_result['total_cis']),
            'currently_available': int(stats_result['currently_available']),
            'currently_unavailable': int(stats_result['total_cis']) - int(stats_result['currently_available']),
            'total_datapoints': int(stats_result['total_datapoints']),
            'total_recording_minutes': float(stats_result['total_recording_minutes']),
            'earliest_timestamp': stats_result['earliest_timestamp'],
            'latest_timestamp': stats_result['latest_timestamp'],
            'overall_uptime_minutes': float(overall_uptime),
            'overall_downtime_minutes': float(overall_downtime),
            'overall_availability_percentage_rollup': float(overall_availability),
            'total_incidents': int(stats_result['total_incidents']),
            'top_unstable_cis': ci_metrics.to_dict('records'),
            'calculated_at': time.time()
        }
# Import packages
import numpy as np
import pandas as pd
import h5py as h5
import requests, json, time, pytz, os
from datetime import datetime
from tzlocal import get_localzone
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
import apprise
import threading
from collections import OrderedDict

# Add dotenv import
import os
from dotenv import load_dotenv
import hmac

# Note: HDF5 cache removed - now using TimescaleDB only

def initialize_data_file(file_name):
    """
    Creates hdf5 file if necessary and builds up basic group structure
    
    Args:
        file_name (str): Path to hdf5 file

    Returns:
        None
    """
    if not(os.path.isfile(file_name)):
        with h5.File(file_name, "w") as f:
            f.create_group("availability")
            f.create_group("configuration_items")

def update_file(file_name, url):
    """
    Gets current data from API and updates hdf5 file with optimized performance

    Args:
        file_name (str): Path to hdf5 file
        url (str): URL of API

    Returns:
        None
    """
    try:
        # Get data from API
        response = requests.get(url, timeout=30)  # Add timeout
        response.raise_for_status()  # Raise exception for bad status codes
        data = json.loads(response.text)
        df = pd.DataFrame(data)
        
        # Check if TimescaleDB is enabled
        config = load_config()
        use_timescaledb = config.get('core', {}).get('timescaledb', {}).get('enabled', False)
        
        # Prepare data for TimescaleDB if enabled
        measurements_data = []
        ci_metadata_data = []
        
        # Batch process data for better performance
        with h5.File(file_name, "a") as f:
            # Pre-define data types
            str_256 = h5.string_dtype(encoding='utf-8', length=256)
            
            # Process all configuration items in batch
            for idx in range(len(df)):
                ci = df.iloc[idx]
                ci_id = str(ci["ci"])
                
                # Availability data
                group_av = f.require_group("availability/" + ci_id)
                av = int(ci["availability"])
                utc_time = datetime.strptime(ci["time"], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)
                timestamp = utc_time.timestamp()
                
                # Create dataset efficiently
                ds = group_av.require_dataset(str(timestamp), shape=(), dtype=int)
                ds[()] = av
                
                # Prepare TimescaleDB data
                if use_timescaledb:
                    measurements_data.append((ci_id, utc_time, av))
                    ci_metadata_data.append((
                        ci_id,
                        str(ci.get("name", "")),
                        str(ci.get("organization", "")),
                        str(ci.get("product", "")),
                        str(ci.get("bu", "")),
                        str(ci.get("tid", "")),
                        str(ci.get("pdt", "")),
                        str(ci.get("comment", ""))
                    ))
                
                # Configuration items
                group_ci = f.require_group("configuration_items/" + ci_id)
                
                # Batch create all properties
                properties = ["tid", "bu", "organization", "pdt", "product", "name", "comment", "time"]
                for property_name in properties:
                    if property_name in ci:
                        ds = group_ci.require_dataset(property_name, shape=(), dtype=str_256)
                        ds[()] = str(ci[property_name])
                
                # Calculate availability difference
                if "current_availability" in group_ci:
                    prev_av = group_ci["current_availability"][()]
                    av_diff = av - prev_av
                else:
                    av_diff = 0
                
                # Set availability data
                group_ci.require_dataset("availability_difference", shape=(), dtype=int)[()] = av_diff
                group_ci.require_dataset("current_availability", shape=(), dtype=int)[()] = av
        
        # Write to TimescaleDB if enabled
        if use_timescaledb and measurements_data:
            try:
                init_timescaledb_schema()
                write_measurements(measurements_data)
                update_ci_metadata(ci_metadata_data)
                print(f"Written {len(measurements_data)} measurements and {len(ci_metadata_data)} CI metadata to TimescaleDB")
            except Exception as e:
                print(f"TimescaleDB write failed (non-fatal): {e}")
        
        # Clear cache after updating file to ensure fresh data
        clear_hdf5_cache()
        
    except requests.RequestException as e:
        print(f"Error fetching data from API: {e}")
        raise
    except Exception as e:
        print(f"Error updating HDF5 file: {e}")
        raise

def get_availability_data_of_ci(file_name, ci):
    """
    Gets availability data for a specific configuration item from TimescaleDB

    Args:
        file_name (str): Path to hdf5 file (kept for compatibility, not used)
        ci (str): ID of the desired confirguration item

    Returns:
        DataFrame: Time series of the availability of the desired configuration item
    """
    try:
        # Get data from TimescaleDB
        with get_db_conn() as conn:
            query = """
            SELECT 
                ts as times,
                status as values
            FROM measurements 
            WHERE ci = %s 
            ORDER BY ts
            """
            df = pd.read_sql_query(query, conn, params=[ci])
            if not df.empty:
                # Convert times to Europe/Berlin timezone
                df['times'] = pd.to_datetime(df['times']).dt.tz_convert('Europe/Berlin')
                return df
            else:
                return pd.DataFrame()
    except Exception as e:
        print(f"Error reading availability data for CI {ci} from TimescaleDB: {e}")
        return pd.DataFrame()

def get_data_of_all_cis(file_name):
    """
    Gets general data for all configuration items from TimescaleDB

    Args:
        file_name (str): Path to hdf5 file (kept for compatibility, not used)

    Returns:
        DataFrame: Basic information about all configuration items
    """
    try:
        # Get data from TimescaleDB
        with get_db_conn() as conn:
            query = """
            SELECT 
                cm.ci,
                cm.name,
                cm.organization,
                cm.product,
                cm.bu,
                cm.tid,
                cm.pdt,
                cm.comment,
                ls.status as current_availability,
                ls.ts as time,
                CASE 
                    WHEN ls.status = 1 AND ls.prev_status = 0 THEN 1 
                    WHEN ls.status = 0 AND ls.prev_status = 1 THEN -1
                    ELSE 0 
                END as availability_difference
            FROM ci_metadata cm
            LEFT JOIN (
                SELECT DISTINCT ON (ci) 
                    ci, 
                    ts, 
                    status,
                    LAG(status) OVER (PARTITION BY ci ORDER BY ts) as prev_status
                FROM measurements 
                ORDER BY ci, ts DESC
            ) ls ON cm.ci = ls.ci
            ORDER BY cm.ci
            """
            df = pd.read_sql_query(query, conn)
            return df
    except Exception as e:
        print(f"Error reading all CIs from TimescaleDB: {e}")
        return pd.DataFrame()

def get_data_of_ci(file_name, ci):
    """
    Gets general data for a specific configuration item from hdf5 file or TimescaleDB

    Args:
        file_name (str): Path to hdf5 file (used for fallback)
        ci (str): ID of the desired confirguration item

    Returns:
        DataFrame: General data of the desired configuration item
    """
    # Check if TimescaleDB is enabled
    config = load_config()
    use_timescaledb = config.get('core', {}).get('timescaledb', {}).get('enabled', False)
    
    if use_timescaledb:
        try:
            # Try to get data from TimescaleDB first
            with get_db_conn() as conn:
                query = """
                SELECT 
                    cm.ci,
                    cm.name,
                    cm.organization,
                    cm.product,
                    cm.bu,
                    cm.tid,
                    cm.pdt,
                    cm.comment,
                    ls.status as current_availability,
                    ls.ts as time,
                    CASE 
                        WHEN ls.status = 1 AND ls.prev_status = 0 THEN 1 
                        ELSE 0 
                    END as availability_difference
                FROM ci_metadata cm
                LEFT JOIN (
                    SELECT DISTINCT ON (ci) 
                        ci, 
                        ts, 
                        status,
                        LAG(status) OVER (PARTITION BY ci ORDER BY ts) as prev_status
                    FROM measurements 
                    WHERE ci = %s
                    ORDER BY ci, ts DESC
                ) ls ON cm.ci = ls.ci
                WHERE cm.ci = %s
                """
                df = pd.read_sql_query(query, conn, params=[ci, ci])
                if not df.empty:
                    return df
        except Exception as e:
            print(f"Error reading CI {ci} from TimescaleDB: {e}")
            return pd.DataFrame()

def pretty_timestamp(timestamp_str):
    """
    Converts UTC timestamp of API to pretty formatted timestamp in local time

    Args:
        timestamp_str (str): UTC timestamp from API

    Returns:
        str: pretty formatted timestamp in local time
    """
    utc_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    berlin_time = utc_time.astimezone(pytz.timezone('Europe/Berlin'))
    formatted_time = berlin_time.strftime('%d.%m.%Y %H:%M:%S Uhr')
    return formatted_time

def send_mail(smtp_settings, recipients, subject, html_message):
    """
    Sends a html-formatted mail to a specified reciepient using SMTP

    Args:
        smtp_settings (dict): host, port, username, password and sender address (from)
        recipients (list of str): list of email addresses
        subject (str): mail subject
        html_message (str): html content of mail

    Returns:
        None
    """
    msg = EmailMessage()
    msg.add_alternative(html_message, subtype='html')
    msg['Subject'] = subject
    msg['From'] = smtp_settings['from']
    msg['Bcc'] = recipients
    s = smtplib.SMTP(
        host = smtp_settings['host'],
        port = smtp_settings['port']
    )
    s.ehlo()
    s.starttls()
    s.login(
        user = smtp_settings['user'],
        password = smtp_settings['password']
    )
    s.send_message(msg)
    s.quit()

def create_html_list_item_for_change(change, home_url):
    """
    Creates a html list item element for a configuration item with changed availability status

    Args:
        change (DataFrame): data for an individual configuration item containing information
        such as organization and product as well as current availability and availability difference
        home_url (str): base url of dash app

    Returns:
        str: html list item element
    """
    if home_url:
        href = home_url + '/plot?ci=' + str(change['ci'])
    else:
        href = ''
    html_str = '<li><strong><a href="' + href + '">' + str(change['ci']) + '</a></strong>: ' + str(change['product']) + ', ' + str(change['name']) + ', ' + str(change['organization']) + ' '
    if change['availability_difference'] == 1:
        html_str += '<span style=color:green>ist wieder verfügbar</span>'
    elif change['availability_difference'] == -1:
        html_str += '<span style=color:red>ist nicht mehr verfügbar</span>'
    else:
        html_str += 'keine Veränderung'
    html_str += ', Stand: ' + str(pretty_timestamp(change['time'])) + '</li>'
    return html_str

def create_notification_message(changes, recipient_name, home_url):
    """
    Creates an HTML formatted message for notifications

    Args:
        changes (DataFrame): DataFrame with availability changes
        recipient_name (str): Name of the recipient
        home_url (str): Base URL of the dashboard

    Returns:
        str: HTML formatted message
    """
    message = f'<html lang="de"><body><p>Hallo {recipient_name},</p>'
    message += '<p>bei der letzten Überprüfung hat sich die Verfügbarkeit der folgenden von Ihnen abonierten Komponenten geändert:</p><ul>'
    
    for index, change in changes.iterrows():
        message += create_html_list_item_for_change(change, home_url)
        
    if home_url:    
        message += f'</ul><p>Den aktuellen Status aller Komponenten können Sie unter <a href="{home_url}">{home_url}</a> einsehen.</p>'
    message += '<p>Weitere Hintergrundinformationen finden Sie im <a href="https://fachportal.gematik.de/ti-status">Fachportal der gematik GmbH</a>.</p><p>Viele Grüße<br>TI-Monitoring</p></body></html>'
    
    return message

def load_apprise_config(notifications_config_file):
    """
    Loads and potentially converts notification configuration for Apprise

    Args:
        notifications_config_file (str): Path to json file with notification configurations

    Returns:
        list: List of notification configurations with Apprise URLs
    """
    with open(notifications_config_file, 'r', encoding='utf-8') as f:
        notification_config = json.load(f)
    
    # Convert legacy configuration to Apprise format if needed
    for config in notification_config:
        # If apprise_urls doesn't exist but recipients does, convert recipients to mailto URLs
        if 'apprise_urls' not in config and 'recipients' in config:
            config['apprise_urls'] = [f"mailto://{recipient}" for recipient in config['recipients']]
        # If neither exists, create empty list
        elif 'apprise_urls' not in config:
            config['apprise_urls'] = []
            
    return notification_config

def send_apprise_notifications(file_name, notifications_config_file, home_url):
    """
    Sends notifications via Apprise for each notification configuration about all
    changes that are relevant for the respective configuration

    Args:
        file_name (str): Path to hdf5 file
        notifications_config_file (str): Path to json file with notification configurations
        home_url (str): base url of dash app

    Returns:
        None
    """
    # Load and potentially convert configuration
    notification_config = load_apprise_config(notifications_config_file)
    
    # Get changes
    ci_data = get_data_of_all_cis(file_name)
    changes = ci_data[ci_data['availability_difference']!=0]
    changes_sorted = changes.sort_values(by = 'availability_difference')
    
    # Process each configuration
    for config in notification_config:
        try:
            # Filter relevant changes
            if (config['type'] == 'whitelist'):
                relevant_changes = changes_sorted[changes_sorted['ci'].isin(config['ci_list'])]
            elif (config['type'] == 'blacklist'):
                relevant_changes = changes_sorted[~changes_sorted['ci'].isin(config['ci_list'])]
                
            number_of_relevant_changes = len(relevant_changes)
            if number_of_relevant_changes > 0:
                # Create notification message
                message = create_notification_message(relevant_changes, config['name'], home_url)
                subject = f'TI-Monitoring: {number_of_relevant_changes} Änderungen der Verfügbarkeit'
                
                # Send via Apprise
                apobj = apprise.Apprise()
                for url in config['apprise_urls']:
                    apobj.add(url)
                apobj.notify(title=subject, body=message, body_format=apprise.NotifyFormat.HTML)
        except Exception as e:
            print(f'Sending notification for profile failed: {e}')
            pass

def send_notifications(file_name, notifications_config_file, smtp_settings, home_url):
    """
    Sends email notifications for each notification configuration about all
    changes that are relevant for the respective configuration

    Args:
        file_name (str): Path to hdf5 file
        notifications_config_file (str): Path to json file with notification configurations
        smtp_settings (dict): host, port, username, password and sender address (from)
        home_url (str): base url of dash app

    Returns:
        None
    """
    # get notification config
    with open(notifications_config_file, 'r', encoding='utf-8') as f:
        notification_config = json.load(f)
    # get changes 
    ci_data = get_data_of_all_cis(file_name)
    changes = ci_data[ci_data['availability_difference']!=0]
    changes_sorted = changes.sort_values(by = 'availability_difference')
    # filter relevant changes for each config and send mails
    for config in notification_config:
        try:
            if (config['type'] == 'whitelist'):
                relevant_changes = changes_sorted[changes_sorted['ci'].isin(config['ci_list'])]
            elif (config['type'] == 'blacklist'):
                relevant_changes = changes_sorted[~changes_sorted['ci'].isin(config['ci_list'])]
            number_of_relevant_changes = len(relevant_changes)
            if number_of_relevant_changes > 0:
                message = '<html lang="de"><body><p>Hallo ' + str(config['name']) + ',</p>'
                message += '<p>bei der letzten Überprüfung hat sich die Verfügbarkeit der folgenden von Ihnen abonierten Komponenten geändert:</p><ul>'
                for index, change in relevant_changes.iterrows():
                    message += create_html_list_item_for_change(change, home_url)
                if home_url:    
                    message += '</ul><p>Den aktuellen Status aller Komponenten können Sie unter <a href="' + home_url + '">' + home_url + '</a> einsehen.</p>'
                message += '<p>Weitere Hintergrundinformationen finden Sie im <a href="https://fachportal.gematik.de/ti-status">Fachportal der gematik GmbH</a>.</p><p>Viele Grüße<br>TI-Monitoring</p></body></html>'
                subject = 'TI-Monitoring: ' + str(number_of_relevant_changes) + ' Änderungen der Verfügbarkeit'
                recipients = config['recipients']
                send_mail(smtp_settings, recipients, subject, message)
        except:
            print('Sending notification for profile failed. Please check notifications config file.')
            pass

def load_env_file():
    """
    Load environment variables from .env file
    
    Returns:
        bool: True if .env file was loaded, False otherwise
    """
    return load_dotenv()

def validate_password(provided_password):
    """
    Validate provided password against environment variable using time-constant comparison
    
    Args:
        provided_password (str): Password provided by user
        
    Returns:
        bool: True if password is valid, False otherwise
    """
    load_env_file()  # Ensure environment variables are loaded
    expected_password = os.getenv('NOTIFICATION_SETTINGS_PASSWORD')
    
    if expected_password is None:
        return False
    
    # Use time-constant comparison to prevent timing attacks
    return hmac.compare_digest(provided_password, expected_password)

def get_notification_config(file_path):
    """
    Read and parse notification configuration
    
    Args:
        file_path (str): Path to notifications.json file
        
    Returns:
        list: List of notification configurations
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error reading notification config: {e}")
        return []

def save_notification_config(file_path, config):
    """
    Save notification configuration to file
    
    Args:
        file_path (str): Path to notifications.json file
        config (list): List of notification configurations
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving notification config: {e}")
        return False

def validate_apprise_urls(urls):
    """
    Validate Apprise URLs
    
    Args:
        urls (list): List of Apprise URLs
        
    Returns:
        bool: True if all URLs are valid, False otherwise
    """
    try:
        for url in urls:
            apobj = apprise.Apprise()
            if not apobj.add(url):
                return False
        return True
    except Exception:
        return False