import os
import requests
from datetime import datetime
import yaml
import smtplib
import json
from time import sleep
from sys import exit

DEFAULT_DELAY = os.getenv('SYSMON_DELAY', 300)
CONFIG_FILE_PATH = os.getenv('SYSMON_CONFIG', "config/config.yml")

def load_config():
    with open(CONFIG_FILE_PATH, 'r') as file:
        configuration = yaml.safe_load(file)
    
    if 'hardware' not in configuration:
        print("Error loading configuration. No hardware provided.")
        exit(1)

    return configuration

def generate_base_url(hardware):
    return "https://www.ovh.com/engine/api/dedicated/server/availabilities?country=UK&hardware={}".format(hardware)

def create_request(base_url):
    resp = requests.get(base_url)
    return resp.json()

def hardware_availability_status(hardware, datacenter_loc):
    url = generate_base_url(hardware)
    resp = create_request(url)

    for region in resp:
        for datacenter in region['datacenters']:
            if datacenter_loc in datacenter['datacenter']:
                return datacenter['availability']

def send_email(config, hardware):
    to = hardware['notifications']
    subject = "SYS hardware {} available!".format(hardware['name'])
    body = "SYS hardware {} available!".format(hardware['name'])

    email_text = """\
From: %s
To: %s
Subject: %s

%s
Link: https://www.soyoustart.com/en/offers/%s.xml
    """ % (config['email']['username'], ", ".join(to), subject, body, hardware['name'])

    try:
        server = smtplib.SMTP(config['email']['server'], config['email']['port'])
        server.ehlo()
        server.starttls()
        server.login(config['email']['username'], config['email']['password'])
        server.sendmail(config['email']['username'], to, email_text)
        server.close()
    except:
        print("Error connecting to SMTP server. Exiting")
        exit(1)

def main():
    configuration = load_config()
    hardware_email_notifications_sent = []

    while True:
        for hardware_check in configuration['hardware']:
            dt = datetime.now()
            hardware_availability = hardware_availability_status(hardware_check['name'], hardware_check['datacenter'])
            log_data = {
                "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
                "hardware": hardware_check['name'],
                "datacenter": hardware_check['datacenter'],
                "availability": hardware_availability if hardware_availability == "unavailable" else "available"
            }

            if hardware_availability != "unavailable":
                if hardware_check['name'] not in hardware_email_notifications_sent:
                    send_email(configuration, hardware_check)
                    log_data['notification_sent'] = True
                    hardware_email_notifications_sent.append(hardware_check['name'])
                else:
                    log_data['notification_sent'] = True

            print(json.dumps(log_data))
            if len(configuration['hardware']) > 1:
                sleep(int(DEFAULT_DELAY))

        sleep(int(DEFAULT_DELAY))

if __name__ == "__main__":
    main()
