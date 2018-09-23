import sys
import requests
import time
import json
import configparser
import os

if sys.version_info[0] < 3:  # Python 3 only. Throws exception if running with Python < 3
    raise Exception("Python 3 or a more recent version is required.")

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'destroy-droplets.cfg'))  # Crontab tweak

DO_API_Key = config['Digital Ocean']['API Key']
droplet_tag = config['Digital Ocean']['Tag']
telegram_URL = config['Telegram']['URL']
telegram_chat_id = config['Telegram']['Chat ID']
no_droplets_notification = config['Notifications']['Notification when no droplets found']
first_warning_time = int(config['Notifications']['First warning time (min)'])
second_warning_time = int(config['Notifications']['Second warning time (min)'])


def get_droplets_list():  # Return 0 if no droplets found and return JSON with droplets if found some

    url = 'https://api.digitalocean.com/v2/droplets?tag_name=%s' % droplet_tag
    headers = {'Authorization': 'Bearer %s' % DO_API_Key}
    r = requests.get(url, headers=headers)
    droplets_list = r.json()
    print('DO response with tagged droplets:', r.text)
    # Count and return droplets number
    global j
    j = json.loads(r.text)
    global droplets_number  # We use this in tg_message_notice()
    droplets_number = ((j['meta'])['total'])  # type = int
    if droplets_number == 0:
        return 0
    else:
        return droplets_list


def tg_message_notice(destroy_time_left):  # Send notification about droplets to delete

    if destroy_time_left == False:
        if no_droplets_notification == 'ON':  # Check if option 'Notification when no droplets found' is enabled
            notice_text = 'No %s droplets found. I\'m done for today' % droplet_tag
        else:
            print('No %s droplets found. I\'m done for today and call sys.exit() now' % droplet_tag)
            sys.exit()
    elif destroy_time_left == True:
        notice_text = 'Successfully destroyed all %s droplets' % droplet_tag
    else:
        droplets_list_info = []
        global droplets_number
        droplets_number_dynamic = droplets_number

        while droplets_number_dynamic > 0:  # Iterate over droplets JSON and get name and IP
            droplet_info = (str(j['droplets'][droplets_number_dynamic - 1]['name']) + ' ' + str(
                (j['droplets'][droplets_number_dynamic - 1]['networks']['v4'][0]['ip_address'])))
            print('droplet_info:\n', droplet_info)
            droplets_list_info.append(droplet_info)
            droplets_number_dynamic = droplets_number_dynamic - 1

        pretty_droplets_list = ('\n'.join(map(str, droplets_list_info)))
        print('destroy_time_left:\n', destroy_time_left)
        notice_text = (
                'I found ' + str(droplets_number) + ' ' + droplet_tag + ' droplets and will delete these in ' + str(
                 round(destroy_time_left / 60)) + ' minutes:\n' + pretty_droplets_list)

    # Send message depends on previous if/else block:
    payload = {'chat_id': telegram_chat_id, 'text': 'Destroy-droplets bot:\n' + notice_text}
    r = requests.get(telegram_URL, params=payload)
    print('tg bot response is:\n' + r.text)


def main():
    url = 'https://api.digitalocean.com/v2/droplets?tag_name=%s' % droplet_tag
    headers = {'Authorization': 'Bearer %s' % DO_API_Key}

    droplets_list = get_droplets_list()
    if droplets_list == 0:
        tg_message_notice(False)  # Send message that no droplets found
    else:

        tg_message_notice(60 * first_warning_time)  # Pass first warning time to tg_message_notice
        time.sleep(60 * (first_warning_time - second_warning_time))  # Wait between first and second warning

        tg_message_notice(60 * second_warning_time)  # Pass second warning time to tg_message_notice
        time.sleep(60 * second_warning_time)  # Wait second warning time

        r = requests.delete(url, headers=headers)  # Destroy request
        print('Destroy request:\n', r.url)
        tg_message_notice(True)  # Send message that droplets have been destroyed


main()
