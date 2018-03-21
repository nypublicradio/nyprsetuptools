import time


def wait(func, args=[], kwargs={}, attempt=1,  backoff=1.33, delay=5,
         exceptions=[], max_attempts=10, wait_for_func=lambda x: True):
    """
    This utility accepts a function, arguments, and keyword arguments
    and will retry the function with the parameters until a successful
    response is received (or until timeout occurs).

    The 'wait_for_func' parameter accepts a callable with a single argument.
    The response of the function will be passed to the callable and if it
    returns a truthy value the waiting will stop.
    eg.
        wait_for_func=lambda x: x.get('key')
        ... would wait until the response dict has a value for 'key'

    The 'exceptions' parameter will consider any provided exceptions as
    failures (preventing them from throwing).

    The default values for backoff, delay,  and max_attempts will retry a func
    for up to 5 minutes (10 times within that timespan).
    """

    if attempt <= max_attempts:
        try:
            resp = func(*args, **kwargs)
            if wait_for_func(resp):
                return resp
        except tuple(exceptions):
            pass
        attempt += 1
        time.sleep(delay)
        delay = backoff * delay
        return wait(func, args, kwargs, attempt=attempt,
                    backoff=backoff, delay=delay, exceptions=exceptions,
                    max_attempts=max_attempts, wait_for_func=wait_for_func)
