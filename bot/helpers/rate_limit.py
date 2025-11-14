import time
from contextlib import suppress

def click_with_rate_limit_checking(driver, job_item, delay=2) -> bool:
    """Click element and detect LinkedIn Easy Apply rate-limit."""

    def snapshot_count():
        return len(getattr(driver, "requests", []))

    def has_new_rate_limit_since(index):
        requests = getattr(driver, "requests", [])[index:]
        for req in requests:
            resp = getattr(req, "response", None)
            status = getattr(resp, "status_code", None) or getattr(resp, "status", None)
            if status == 429:
                return True
        return False

    if not (job_item.is_displayed() and job_item.is_enabled()):
        return False

    snap = snapshot_count()

    with suppress(Exception):
        job_item.click()
    time.sleep(delay)

    if not has_new_rate_limit_since(snap):
        return True

    time.sleep(delay * 2)
    return False
