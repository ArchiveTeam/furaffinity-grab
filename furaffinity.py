import sys

wpull_hook = globals().get('wpull_hook')  # silence code checkers

counter = 0


def engine_run():
    print('    Hello world!')
    sys.stdout.flush()


def resolve_dns(host):
    pass


def accept_url(url_info, record_info, verdict, reasons):
    return verdict


def queued_url(url_info):
    global counter
    print('    queued_url', url_info['url'])
    sys.stdout.flush()
    counter += 1


def dequeued_url(url_info, record_info):
    global counter
    print('    dequeued_url', url_info['url'])
    sys.stdout.flush()
    counter -= 1


def handle_pre_response(url_info, record_info, http_info):
    return wpull_hook.actions.NORMAL


def handle_response(url_info, record_info, http_info):
    return wpull_hook.actions.NORMAL


def handle_error(url_info, record_info, error_info):
    return wpull_hook.actions.NORMAL


def get_urls(filename, url_info, document_info):
    return None


def wait_time(seconds):
    return seconds


def finish_statistics(start_time, end_time, num_urls, bytes_downloaded):
    pass


def exit_status(exit_code):
    return exit_code


wpull_hook.callbacks.engine_run = engine_run
wpull_hook.callbacks.resolve_dns = resolve_dns
wpull_hook.callbacks.accept_url = accept_url
wpull_hook.callbacks.queued_url = queued_url
wpull_hook.callbacks.dequeued_url = dequeued_url
wpull_hook.callbacks.handle_pre_response = handle_pre_response
wpull_hook.callbacks.handle_response = handle_response
wpull_hook.callbacks.handle_error = handle_error
wpull_hook.callbacks.get_urls = get_urls
wpull_hook.callbacks.wait_time = wait_time
wpull_hook.callbacks.finish_statistics = finish_statistics
wpull_hook.callbacks.exit_status = exit_status
