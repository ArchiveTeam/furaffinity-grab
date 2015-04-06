import codecs
import os
import sys
import time
import re

wpull_hook = globals().get('wpull_hook')  # silence code checkers
tries = 0
total_tries = 0
max_gallery_page = None
max_scraps_page = None
max_favorites_page = None
item_dir = os.environ['item_dir']


def print_(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def accept_url(url_info, record_info, verdict, reasons):
    global max_gallery_page
    global max_scraps_page

    url = url_info['url']

    if verdict:
        match = re.search(r'furaffinity\.net/(\w+)/([^/]+)/(\d+)/', url)

        if match:
            what_type = match.group(1).lower()

            if what_type in ('gallery', 'scraps', 'favorites'):
                num = int(match.group(3))

                if what_type == 'gallery':
                    if max_gallery_page is not None and num > max_gallery_page:
                        print_('Pagination complete for gallery')
                        return False
                elif what_type == 'scraps':
                    if max_scraps_page is not None and num > max_scraps_page:
                        print_('Pagination complete for scraps')
                        return False
                elif what_type == 'favorites':
                    if max_favorites_page is not None and num > max_favorites_page:
                        print_('Pagination complete for favorites')
                        return False
                else:
                    raise Exception('Unknown what type!')

        if '/themes/classic/img/' in url_info['url']:
            return False
        if 'google-analytics.com' in url_info['url']:
            return False
        if 'google.com/analytics' in url_info['url']:
            return False
        if 'gstatic.com/analytics' in url_info['url']:
            return False
        if re.search(r'/commissions/.*/(add|manage)/$', url_info['url']):
            return False

    return verdict


def handle_pre_response(url_info, record_info, response_info):
    return wpull_hook.actions.NORMAL


def handle_response(url_info, record_info, response_info):
    global tries
    global total_tries
    total_tries += 1

    if total_tries > 1000:
        raise Exception('Too many tries in this session!')

    status_code = response_info['status_code']

    if status_code != 404 and status_code >= 400:
        print_('Uh oh!. Sleeping...')
        time.sleep(60)
        tries += 1

        if tries > 5:
            raise Exception('Giving up')
        else:
            return wpull_hook.actions.RETRY

    tries = 0


    return wpull_hook.actions.NORMAL


def handle_error(url_info, record_info, error_info):
    global tries
    global total_tries
    total_tries += 1

    if total_tries > 1000:
        raise Exception('Too many tries in this session!')

    tries += 1
    if tries > 5:
        raise Exception('Giving up')

    return wpull_hook.actions.NORMAL


def get_urls(filename, url_info, document_info):
    urls = []

    if 'furaffinity.net' in url_info['hostname']:
        with open(filename, 'r', encoding='utf8', errors='replace') as file:
            text = file.read(1048576)

        check_ok_content(text)

        if not is_text_404(text):
            with open(os.path.join(item_dir, 'usernames.txt'), 'a', encoding='utf8', errors='replace') as file:
                for username in scrape_usernames(text):
                    file.write(username)
                    file.write('\n')

            url = url_info['url']
            check_pagination(text, url)

        print_('Looking good so far..')

    return urls


def check_ok_content(text):
    ok_text_found = (
        'Page generated in' in text or
        'This user cannot be found.' in text
    )

    is_404_error_page = is_text_404(text)

    if ok_text_found and not is_404_error_page and '/logout/' not in text:
        print_('Problem detected. Not logged in! Sleeping.')
        time.sleep(60)
        raise Exception('Not logged in!')
    elif ok_text_found and not is_404_error_page and 'Toggle to hide Mature and Adult submissions.' not in text:
        print_('Problem detected. Cannot view adult material! Sleeping.')
        time.sleep(60)
        raise Exception('Cannot view adult material!')


def is_text_404(text):
    is_404_error_page = (
        'This user cannot be found.' in text or
        'This user has voluntarily disabled access to their userpage.' in text
    )
    return is_404_error_page


def scrape_usernames(text):
    for match in re.finditer(r'href="/user/([^"]+)"', text):
        username = match.group(1)
        username = username.strip('/')
        yield username


def check_pagination(text, url):
    global max_gallery_page
    global max_scraps_page
    global max_favorites_page

    match = re.search(r'furaffinity\.net/(\w+)/([^/]+)/(\d+)/', url)

    if match:
        # if codecs.encode('kzyuggc_znxrf_gebtqbe_fnq', 'rot_13') not in text:
        #     raise Exception('Could not find pagination form!')

        what_type = match.group(1).lower()

        if what_type in ('gallery', 'scraps', 'favorites') and 'There are no submissions to list' in text:
            num = int(match.group(3))

            if what_type == 'gallery':
                if max_gallery_page is None:
                    max_gallery_page = num
            elif what_type == 'scraps':
                if max_scraps_page is None:
                    max_scraps_page = num
            elif what_type == 'favorites':
                if max_favorites_page is None:
                    max_favorites_page = num
            else:
                raise Exception('Unknown what type!')


def wait_time(seconds, url_info, url_record, response, error):
    if 'facdn.net' in url_info['hostname'] and not error:
        return 0
    else:
        return seconds


# wpull_hook.callbacks.engine_run = engine_run
# wpull_hook.callbacks.resolve_dns = resolve_dns
wpull_hook.callbacks.accept_url = accept_url
# wpull_hook.callbacks.queued_url = queued_url
# wpull_hook.callbacks.dequeued_url = dequeued_url
wpull_hook.callbacks.handle_pre_response = handle_pre_response
wpull_hook.callbacks.handle_response = handle_response
wpull_hook.callbacks.handle_error = handle_error
wpull_hook.callbacks.get_urls = get_urls
wpull_hook.callbacks.wait_time = wait_time
# wpull_hook.callbacks.finish_statistics = finish_statistics
# wpull_hook.callbacks.exit_status = exit_status
wpull_hook.callbacks.version = 3
