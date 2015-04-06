from __future__ import print_function
import base64
import codecs
import cookielib
import json
import os
import random
import socket
import time

import requests
import requests.exceptions
import sys
import pickle


def print_(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def main():
    command = sys.argv[1]
    user_agent = os.environ['user_agent']
    disco_tracker = os.environ['disco_tracker']
    item_dir = os.environ['item_dir']

    if 'bind_address' in os.environ:
        # https://stackoverflow.com/questions/1150332/source-interface-with-python-and-urllib2
        real_socket_socket = socket.socket
        def bound_socket(*a, **k):
            sock = real_socket_socket(*a, **k)
            sock.bind((os.environ['bind_address'], 0))
            return sock
        socket.socket = bound_socket

    requests_session = requests.Session()
    requests_session.cookies = cookie_jar = cookielib.MozillaCookieJar(os.path.join(item_dir, 'cookies.txt'))
    state = {
        'logged_in': False
    }

    def fetch(url, method='get', data=None, expect_status=200, headers=None):
        headers = {'user-agent': user_agent}

        if headers:
            headers.update(headers)

        for try_num in range(5):
            print_('Fetch', url, '...', end='')

            if method == 'get':
                response = requests_session.get(url, headers=headers, timeout=60)
            elif method == 'post':
                response = requests_session.post(url, headers=headers, data=data, timeout=60)
            else:
                raise Exception('Unknown method')

            print_(str(response.status_code))

            ok_text_found = (
                'Page generated in' in response.text or
                'This user cannot be found.' in response.text
            )

            is_404_error_page = (
                'This user cannot be found.' in response.text
            )

            if response.status_code != expect_status and not ok_text_found:
                print_('Problem detected. Sleeping.')
                time.sleep(60)
            elif ok_text_found and not is_404_error_page and state['logged_in'] and '/logout/' not in response.text:
                print_('Problem detected. Not logged in! Sleeping.')
                time.sleep(60)
                raise Exception('Not logged in!')
            elif ok_text_found and not is_404_error_page and state['logged_in'] and 'Toggle to hide Mature and Adult submissions.' not in response.text:
                print_('Problem detected. Cannot view adult material! Sleeping.')
                time.sleep(60)
                raise Exception('Cannot view adult material!')
            else:
                time.sleep(random.uniform(0.5, 1.5))
                return response

        raise Exception('Giving up!')

    def login():
        assert not state['logged_in']

        for try_count in range(10):
            print_('Get login secrets...', end='')
            try:
                response = requests.post(
                    disco_tracker + '/api/get_secrets?v=1',
                    timeout=60
                )
            except requests.exceptions.ConnectionError:
                print_('Connection error.')
                print_('Sleeping...')
                time.sleep(60)
            else:
                print_(response.status_code)

                if response.status_code == 200:
                    break
                else:
                    print_('Sleeping...')
                    time.sleep(60)
        else:
            raise Exception('Could not get secrets!')

        secrets_doc = json.loads(response.text)
        username = secrets_doc['username']
        password = base64.b64decode(secrets_doc['password'].encode('ascii')).decode('ascii')

        fetch(
            'https://www.furaffinity.net/' + 'login/?ref=https://www.furaffinity.net/',
            method='post', expect_status=302,
            headers={
                'origin': 'https://www.furaffinity.net',
                'pragma': 'no-cache',
                'referer': 'https://www.furaffinity.net/' + 'login/',
                },
            data={
                'action': 'login',
                'retard_protection': '1',
                'name': username,
                'pass': password,
                'login': codecs.encode('Ybtva gb SheNssvavgl', 'rot_13'),
                }
        )

        state['logged_in'] = True

        fetch('https://www.furaffinity.net/')

    def logout():
        assert state['logged_in']
        state['logged_in'] = False
        fetch('https://www.furaffinity.net/logout/', expect_status=302)

    if command == 'begin':
        login()

        print_('Save cookies.')
        cookie_jar.save()
    elif command == 'end':
        state['logged_in'] = True

        print_('Load cookies')
        cookie_jar.load()

        logout()

        scraped_usernames = set()

        with open(os.path.join(item_dir, 'usernames.txt'), 'r') as file:
            for line in file:
                scraped_usernames.add(line.strip())

        results = {
            'discovered_usernames': tuple(scraped_usernames),
            'username_disabled_map': {}
        }

        upload_username_results(results, disco_tracker, scraped_from_private=True)
    else:
        raise Exception('Unknown command.')


def upload_username_results(results, tracker_url, scraped_from_private=False):
    if scraped_from_private:
        url = tracker_url + '/api/user_private_discovery'
    else:
        url = tracker_url + '/api/user_discovery'

    for try_count in range(10):
        print_('Uploading results...', end='')
        try:
            response = requests.post(
                url,
                data=json.dumps(results).encode('ascii'),
                timeout=60
            )
        except requests.exceptions.ConnectionError:
            print_('Connection error.')
            print_('Sleeping...')
            time.sleep(60)
        else:
            print_(response.status_code)

            if response.status_code == 200:
                return
            else:
                print_('Sleeping...')
                time.sleep(60)

    raise Exception('Failed to upload.')


if __name__ == '__main__':
    main()
