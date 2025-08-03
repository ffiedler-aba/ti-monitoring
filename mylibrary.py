# Import packages
import numpy as np
import pandas as pd
import h5py as h5
import requests, json, time, pytz, os
from datetime import datetime
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText

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
    Gets current data from API and updates hdf5 file

    Args:
        file_name (str): Path to hdf5 file
        url (str): URL of API

    Returns:
        None
    """
    data = json.loads(requests.get(url).text)
    df = pd.DataFrame(data)
    with h5.File(file_name, "a") as f:
        for idx in range(len(df)):
            ci = df.iloc[idx]
            # availybility
            group_av = f.require_group("availability/" + str(ci["ci"]))
            av = int(ci["availability"])
            timestamp = datetime.strptime(ci["time"], '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
            ds = group_av.require_dataset(str(timestamp),shape=(),dtype=int)
            ds[()] = av
            # configuration items
            group_ci = f.require_group("configuration_items/" + str(ci["ci"]))
            str_256 = h5.string_dtype(encoding='utf-8', length=256)
            for property in ["tid", "bu", "organization", "pdt", "product", "name", "comment", "time"]:
                ds = group_ci.require_dataset(property, shape=(), dtype=str_256)
                ds[()] = ci[property]
            if "current_availability" in group_ci:
                prev_av = group_ci["current_availability"][()]
                av_diff = av - prev_av
            else:
                av_diff = 0
            ds = group_ci.require_dataset("availability_difference",shape=(),dtype=int)
            ds[()] = av_diff
            ds = group_ci.require_dataset("current_availability",shape=(),dtype=int)
            ds[()] = av

def get_availability_data_of_ci(file_name, ci):
    """
    Gets availability data for a specific configuration item from hdf5 file

    Args:
        file_name (str): Path to hdf5 file
        ci (str): ID of the desired confirguration item

    Returns:
        DataFrame: Time series of the availability of the desired configuration item
    """
    all_ci_data = []
    with h5.File(file_name, 'r') as f:
        group = f["availability/" + ci]
        ci_data = {}
        times = []
        values = []
        for name, dataset in group.items():
            if isinstance(dataset, h5.Dataset):
                time = pd.to_datetime(float(name), unit='s').tz_localize('UTC').tz_convert('Europe/Berlin')
                times.append(time)
                values.append(int(dataset[()]))
        ci_data["times"] = np.array(times)
        ci_data["values"] = np.array(values)
        return pd.DataFrame(ci_data)

def get_data_of_all_cis(file_name):
    """
    Gets general data for all configuration items from hdf5 file such as organization
    and product as well as current availability and availability difference

    Args:
        file_name (str): Path to hdf5 file

    Returns:
        DataFrame: Basic information about all configuration items
    """
    all_ci_data = []
    with h5.File(file_name, 'r') as f:
        group = f["configuration_items"]
        cis = group.keys()
        for ci in cis:
            group = f["configuration_items/"+ci]
            ci_data = {}
            ci_data["ci"] = ci
            for name in group:
                dataset = group[name]
                value = dataset[()]
                # Handle scalar bytes (decode)
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                ci_data[name] = value
            #df = pd.DataFrame(ci_data)
            all_ci_data.append(ci_data)
    return pd.DataFrame(all_ci_data)

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

def send_mail(smtp_settings, recipient, subject, html_message):
    """
    Sends a html-formatted mail to a specified reciepient using SMTP

    Args:
        smtp_settings (dict): host, port, username, password and sender address (from)

    Returns:
        None
    """
    msg = EmailMessage()
    msg.add_alternative(html_message, subtype='html')
    msg['Subject'] = subject
    msg['From'] = smtp_settings['from']
    msg['To'] = recipient
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

def create_html_list_item_for_change(change):
    """
    Creates a html list item element for a configuration item with changed availability status

    Args:
        change (DataFrame): data for an individual configuration item containing information
        such as organization and product as well as current availability and availability difference

    Returns:
        str: html list item element
    """
    html_str = '<li><strong>' + str(change['ci']) + ': ' + str(change['name']) + '</strong>, ' + str(change['organization']) + ' '
    if change['availability_difference'] == 1:
        html_str += '<span style=color:green>ist wieder verfügbar</span>'
    elif change['availability_difference'] == -1:
        html_str += '<span style=color:red>ist nicht mehr verfügbar</span>'
    else:
        html_str += 'keine Veränderung'
    html_str += ', Stand: ' + str(pretty_timestamp(change['time'])) + '</li>'
    return html_str

def send_notifications(file_name, notifications_config_file, smtp_settings):
    """
    Sends email notifications for each notification configuration about all
    changes that are relevant for the respective configuration

    Args:
        file_name (str): Path to hdf5 file
        notifications_config_file (str): Path to json file with notification configurations
        smtp_settings (dict): host, port, username, password and sender address (from)

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
        if (config['type'] == 'whitelist'):
            relevant_changes = changes_sorted[changes_sorted['ci'].isin(config['ci_list'])]
        elif (config['type'] == 'blacklist'):
            relevant_changes = changes_sorted[~changes_sorted['ci'].isin(config['ci_list'])]
        number_of_relevant_changes = len(relevant_changes)
        if number_of_relevant_changes > 0:
            message = '<html lang="de"><body><p>Hallo ' + str(config['name']) + ',</p>'
            message += '<p>bei der letzten Überprüfung hat sich die Verfügbarkeit der folgenden von Ihnen abonierten Kompnenten geändert:</p><ul>'
            for index, change in relevant_changes.iterrows():
                message += create_html_list_item_for_change(change)
            message += '</ul><p>Den aktuellen Status können Sie unter <a href="https://ti-monitoring.lukas-schmidt-russnak.de">https://ti-monitoring.lukas-schmidt-russnak.de</a> einsehen.</p><p>Viele Grüße<br>TI-Monitoring</p></body></html>'
            subject = 'TI-Monitoring: ' + str(number_of_relevant_changes) + ' Änderungen der Verfügbarkeit'
            recipient = config['mail']
            send_mail(smtp_settings, recipient, subject, message)

def main():
    return

if __name__ == '__main__':
    main()