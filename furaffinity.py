import sys
import time

wpull_hook = globals().get('wpull_hook')  # silence code checkers
tries = 0
total_tries = 0


def print_(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def accept_url(url_info, record_info, verdict, reasons):
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
    if 'furaffinity.net' in url_info['hostname']:
        with open(filename, 'r') as file:
            check_ok_content(file.read(1048576))


    return None


def check_ok_content(text):
    ok_text_found = (
        'Page generated in' in text or
        'This user cannot be found.' in text
    )

    is_404_error_page = (
        'This user cannot be found.' in text or
        'This user has voluntarily disabled access to their userpage.' in text
    )

    if ok_text_found and not is_404_error_page and '/logout/' not in text:
        print_('Problem detected. Not logged in! Sleeping.')
        time.sleep(60)
        raise Exception('Not logged in!')
    elif ok_text_found and not is_404_error_page and 'Toggle to hide Mature and Adult submissions.' not response.text:
        print_('Problem detected. Cannot view adult material! Sleeping.')
        time.sleep(60)
        raise Exception('Cannot view adult material!')


# wpull_hook.callbacks.engine_run = engine_run
# wpull_hook.callbacks.resolve_dns = resolve_dns
wpull_hook.callbacks.accept_url = accept_url
# wpull_hook.callbacks.queued_url = queued_url
# wpull_hook.callbacks.dequeued_url = dequeued_url
wpull_hook.callbacks.handle_pre_response = handle_pre_response
wpull_hook.callbacks.handle_response = handle_response
wpull_hook.callbacks.handle_error = handle_error
wpull_hook.callbacks.get_urls = get_urls
# wpull_hook.callbacks.wait_time = wait_time
# wpull_hook.callbacks.finish_statistics = finish_statistics
# wpull_hook.callbacks.exit_status = exit_status
