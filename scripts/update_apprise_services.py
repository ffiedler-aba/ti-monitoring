#!/usr/bin/env python3
"""
Script to update apprise_services.json from the Apprise Wiki
This script scrapes the Apprise Wiki to get the latest service information
"""

import json
import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path

def get_wiki_services():
    """Scrape services from Apprise Wiki"""
    try:
        # Get the main wiki page
        response = requests.get('https://github.com/caronc/apprise/wiki', timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the notification services section
        services = {}
        
        # Look for service links in the wiki
        # The wiki has links to individual service pages
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/wiki/Notify_' in href:
                service_name = href.split('/wiki/Notify_')[-1]
                service_display = link.get_text().strip()
                
                if service_name and service_display:
                    # Clean up the service display name
                    # Remove "Notify_" prefix and convert to proper case
                    clean_name = service_display.replace('Notify_', '').replace('_', ' ')
                    
                    # Handle special cases for better display names
                    special_names = {
                        'msteams': 'Microsoft Teams',
                        'tgram': 'Telegram',
                        'pover': 'Pushover',
                        'pbul': 'Pushbullet',
                        'mmost': 'Mattermost',
                        'ses': 'AWS SES',
                        'json': 'Webhook (JSON)',
                        'form': 'Form POST',
                        'xml': 'XML POST',
                        'hassio': 'Home Assistant',
                        'rsyslog': 'Rsyslog',
                        'splunk': 'Splunk'
                    }
                    
                    if service_name in special_names:
                        clean_name = special_names[service_name]
                    else:
                        # Convert to title case
                        clean_name = clean_name.title()
                    
                    # Determine category based on service name
                    category = categorize_service(service_name)
                    
                    # Determine priority (1=high, 2=medium, 3=low)
                    priority = get_service_priority(service_name)
                    
                    # Generate example URL
                    example = generate_example_url(service_name)
                    
                    # Generate wiki URL
                    wiki_url = generate_wiki_url(service_name)
                    
                    services[service_name] = {
                        'name': clean_name,
                        'category': category,
                        'example': example,
                        'description': f'{clean_name} Benachrichtigungen',
                        'priority': priority,
                        'wiki_url': wiki_url
                    }
        
        return services
    
    except Exception as e:
        print(f"Error scraping wiki: {e}")
        return {}

def categorize_service(service_name):
    """Categorize service based on name"""
    service_lower = service_name.lower()
    
    if any(x in service_lower for x in ['slack', 'teams', 'telegram', 'discord', 'whatsapp', 'signal', 'matrix', 'mattermost', 'rocket', 'flock', 'guilded']):
        return 'Messaging'
    elif any(x in service_lower for x in ['mail', 'email', 'smtp', 'gmail', 'outlook', 'ses', 'sendgrid', 'mailgun', 'resend']):
        return 'Email'
    elif any(x in service_lower for x in ['push', 'pushover', 'pushbullet', 'gotify', 'ntfy', 'prowl']):
        return 'Push'
    elif any(x in service_lower for x in ['sms', 'twilio', 'clickatell', 'bulksms', 'messagebird']):
        return 'SMS'
    elif any(x in service_lower for x in ['webhook', 'json', 'form', 'xml', 'http']):
        return 'Custom'
    elif any(x in service_lower for x in ['mqtt', 'hassio', 'homeassistant', 'kodi', 'xbmc']):
        return 'IoT'
    elif any(x in service_lower for x in ['syslog', 'rsyslog', 'splunk']):
        return 'Logging'
    elif any(x in service_lower for x in ['pagerduty', 'opsgenie', 'jira', 'ifttt']):
        return 'Monitoring'
    else:
        return 'Other'

def get_service_priority(service_name):
    """Determine service priority"""
    service_lower = service_name.lower()
    
    # High priority services (most popular)
    high_priority = ['slack', 'teams', 'telegram', 'discord', 'email', 'gmail', 'outlook', 'pushover']
    
    # Medium priority services
    medium_priority = ['whatsapp', 'signal', 'matrix', 'mattermost', 'rocket', 'pushbullet', 'gotify', 'ntfy', 'twilio', 'aws_ses', 'sendgrid', 'mailgun', 'resend', 'pagerduty', 'opsgenie']
    
    if any(x in service_lower for x in high_priority):
        return 1
    elif any(x in service_lower for x in medium_priority):
        return 2
    else:
        return 3

def generate_wiki_url(service_name):
    """Generate wiki URL for service"""
    # Convert service name to wiki format
    # Remove special characters and convert to lowercase
    wiki_name = service_name.lower()
    wiki_name = wiki_name.replace(' ', '_')
    wiki_name = wiki_name.replace('-', '_')
    wiki_name = wiki_name.replace('(', '')
    wiki_name = wiki_name.replace(')', '')
    wiki_name = wiki_name.replace('.', '')
    
    # Handle special cases
    special_cases = {
        'msteams': 'msteams',
        'tgram': 'telegram',
        'pover': 'pushover',
        'pbul': 'pushbullet',
        'mmost': 'mattermost',
        'ses': 'aws_ses',
        'json': 'json',
        'form': 'form',
        'xml': 'xml',
        'hassio': 'homeassistant'
    }
    
    if wiki_name in special_cases:
        wiki_name = special_cases[wiki_name]
    
    return f"https://github.com/caronc/apprise/wiki/Notify_{wiki_name}"

def generate_example_url(service_name):
    """Generate example URL for service based on actual Apprise documentation"""
    service_lower = service_name.lower()
    
    # Common URL patterns based on actual Apprise documentation
    if 'slack' in service_lower:
        return 'slack://BOT_TOKEN@WORKSPACE/CHANNEL'
    elif 'teams' in service_lower or 'msteams' in service_lower:
        return 'msteams://TOKEN@TEAM_ID/CHANNEL_ID'
    elif 'telegram' in service_lower or 'tgram' in service_lower:
        return 'tgram://BOT_TOKEN/CHAT_ID'
    elif 'discord' in service_lower:
        return 'discord://WEBHOOK_ID/WEBHOOK_TOKEN'
    elif 'email' in service_lower and 'mailgun' not in service_lower and 'gmail' not in service_lower and 'outlook' not in service_lower:
        return 'mailto://USERNAME:PASSWORD@SMTP_SERVER:PORT'
    elif 'gmail' in service_lower:
        return 'gmail://USERNAME:APP_PASSWORD@gmail.com'
    elif 'outlook' in service_lower:
        return 'outlook://USERNAME:PASSWORD@outlook.com'
    elif 'mailgun' in service_lower:
        return 'mailgun://USER@DOMAIN/API_KEY/'
    elif 'whatsapp' in service_lower:
        return 'whatsapp://TOKEN@FROM_NUMBER'
    elif 'signal' in service_lower:
        return 'signal://USERNAME:PASSWORD@SIGNAL_SERVER'
    elif 'matrix' in service_lower:
        return 'matrix://USERNAME:PASSWORD@MATRIX_SERVER/ROOM_ID'
    elif 'mattermost' in service_lower or 'mmost' in service_lower:
        return 'mmost://USERNAME:PASSWORD@MATTERMOST_SERVER/CHANNEL'
    elif 'rocket' in service_lower:
        return 'rocket://USERNAME:PASSWORD@ROCKET_SERVER/CHANNEL'
    elif 'pushover' in service_lower or 'pover' in service_lower:
        return 'pover://USER_KEY@APP_TOKEN'
    elif 'pushbullet' in service_lower or 'pbul' in service_lower:
        return 'pbul://ACCESS_TOKEN'
    elif 'gotify' in service_lower:
        return 'gotify://TOKEN@GOTIFY_SERVER'
    elif 'ntfy' in service_lower:
        return 'ntfy://TOPIC@NTFY_SERVER'
    elif 'twilio' in service_lower:
        return 'twilio://ACCOUNT_SID:AUTH_TOKEN@FROM_NUMBER'
    elif 'ses' in service_lower:
        return 'ses://ACCESS_KEY:SECRET_KEY@REGION'
    elif 'sendgrid' in service_lower:
        return 'sendgrid://API_KEY@SENDGRID'
    elif 'resend' in service_lower:
        return 'resend://API_KEY@resend.com'
    elif 'webhook' in service_lower or 'json' in service_lower:
        return 'json://WEBHOOK_URL'
    elif 'form' in service_lower:
        return 'form://WEBHOOK_URL'
    elif 'xml' in service_lower:
        return 'xml://WEBHOOK_URL'
    elif 'mqtt' in service_lower:
        return 'mqtt://USERNAME:PASSWORD@MQTT_SERVER:PORT/TOPIC'
    elif 'syslog' in service_lower:
        return 'syslog://SYSLOG_SERVER:PORT'
    elif 'rsyslog' in service_lower:
        return 'rsyslog://SYSLOG_SERVER:PORT'
    elif 'splunk' in service_lower:
        return 'splunk://TOKEN@SPLUNK_SERVER:PORT/INDEX'
    elif 'pagerduty' in service_lower:
        return 'pagerduty://INTEGRATION_KEY'
    elif 'opsgenie' in service_lower:
        return 'opsgenie://API_KEY@OPSGENIE'
    elif 'jira' in service_lower:
        return 'jira://USERNAME:PASSWORD@JIRA_SERVER/PROJECT'
    elif 'ifttt' in service_lower:
        return 'ifttt://WEBHOOK_KEY/EVENT_NAME'
    elif 'hassio' in service_lower or 'homeassistant' in service_lower:
        return 'hassio://ACCESS_TOKEN@HOMEASSISTANT_SERVER'
    else:
        return f'{service_name}://USERNAME:PASSWORD@SERVER'

def update_services_file():
    """Update the apprise_services.json file"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    services_file = project_root / 'apprise_services.json'
    
    print("Updating Apprise services from wiki...")
    
    # Get services from wiki
    wiki_services = get_wiki_services()
    
    if not wiki_services:
        print("No services found from wiki, keeping existing file")
        return
    
    # Load existing services to preserve manual additions
    existing_services = {}
    if services_file.exists():
        try:
            with open(services_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_services = data.get('services', {})
        except Exception as e:
            print(f"Error loading existing services: {e}")
    
    # Merge services (wiki takes precedence for existing, keep manual additions)
    merged_services = {**existing_services, **wiki_services}
    
    # Sort services by priority and name
    sorted_services = dict(sorted(
        merged_services.items(),
        key=lambda x: (x[1].get('priority', 3), x[1].get('name', ''))
    ))
    
    # Create new data structure
    new_data = {
        'services': sorted_services,
        'last_updated': str(Path(__file__).stat().st_mtime),
        'total_services': len(sorted_services)
    }
    
    # Write to file
    try:
        with open(services_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        
        print(f"Updated {len(sorted_services)} services in {services_file}")
        print(f"Categories: {set(s.get('category', 'Other') for s in sorted_services.values())}")
        
    except Exception as e:
        print(f"Error writing services file: {e}")

if __name__ == '__main__':
    update_services_file()
