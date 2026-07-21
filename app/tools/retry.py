import time

def call_with_retry(func, *args, retries=3, delay=3, **kwargs):
    """Retries a flaky external call (LLM/API) up to `retries` times before giving up."""
    last_error = None
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            time.sleep(delay)
    raise last_error