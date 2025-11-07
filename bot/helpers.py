import random
import time
from typing import Optional, List, Iterable, Tuple
from contextlib import suppress
from loguru import logger
from selenium import webdriver
from selenium.common import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from bot.settings import settings
from bot.enums import ElementsEnum, WorkTypesEnum


# ==========================================
# Page state checks
# ==========================================
def has_exhausted_limit(driver) -> bool:
    xpath = (
        "//*[text()=\"You’ve reached today's Easy Apply limit. "
        "Great effort applying today. We limit daily submissions "
        'to help ensure each application gets the right attention."]'
    )
    return bool(driver.find_elements(By.XPATH, xpath))


def has_offsite_apply_icon(driver) -> bool:
    """Check if page has offsite apply icon."""
    return bool(driver.find_elements(By.CSS_SELECTOR, ElementsEnum.OFFSITE_APPLY_ICON))


def body_has_text(driver, text: str) -> bool:
    """Return True if the given text is present in <body>."""
    body = driver.find_element(By.TAG_NAME, "body")
    return text in body.text


# ==========================================
# DOM utilities
# ==========================================


def get_children(driver, root) -> List[WebElement]:
    if root is None:
        root_el = driver.find_element(By.TAG_NAME, "body")
    elif isinstance(root, tuple):
        by_loc, val = root
        root_el = driver.find_element(by_loc, val)
    else:
        root_el = root
    return root_el.find_elements(By.XPATH, "./*")


def find_elements(driver, by, selector, index=0, retries=0):
    for attempt in range(retries + 1):
        try:
            return driver.find_elements(by, selector)[index]
        except Exception:
            time.sleep(settings.DELAY_TIME + random.uniform(1, 2))

    raise Exception(f"Could not find element {selector} in {retries} attempts")


def click_if_exists(driver, by, selector, index=0, retries=0) -> bool:
    """Try to find and click element if clickable. Return True if clicked."""
    if body_has_text(driver, "Job search safety reminder"):
        driver.find_element(By.CSS_SELECTOR, "[data-test-modal-close-btn]").click()

    for attempt in range(retries + 1):
        try:
            driver.find_elements(by, selector)[index].click()
            return True
        except Exception:
            time.sleep(settings.DELAY_TIME + random.uniform(1, 2))
            if attempt == retries:
                return False
    return False


def click_with_rate_limit_checking(driver, job_item, delay=2) -> bool:
    """Click element and detect LinkedIn's Easy Apply rate-limit."""

    def snapshot_count():
        return len(getattr(driver, "requests", []))

    def has_new_rate_limit_since(index):
        requests = getattr(driver, "requests", [])[index:]
        for req in requests:
            resp = getattr(req, "response", None)
            if (
                resp
                and (
                    getattr(resp, "status_code", None) or getattr(resp, "status", None)
                )
                == 429
            ):
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


# ==========================================
# URL + safe operations
# ==========================================


def build_job_url(
    keyword: Optional[str] = None,
    country_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> str:
    """Build LinkedIn job search URL."""
    base_url = settings.LINKEDIN_BASE_URL

    if job_id:
        return f"{base_url}/jobs/search?currentJobId={job_id}"

    params = {}
    if keyword:
        params["keywords"] = f'"{keyword.strip()}"'
    if country_id:
        params["geoId"] = country_id

    params["f_TPR"] = f"r{settings.JOB_SEARCH_TIME_WINDOW}"
    params["f_WT"] = WorkTypesEnum(settings.WORK_TYPE)

    query = "&".join(f"{k}={v}" for k, v in params.items() if v)
    return f"{base_url}/jobs/search?{query}"


def safe_find_element(driver, by, value, *, retries=3, delay=1):
    """Find element safely with retries."""
    for attempt in range(retries):
        try:
            return driver.find_element(by, value)
        except NoSuchElementException:
            if attempt == retries - 1:
                logger.warning(f"⚠️ Element not found: {value}")
        except StaleElementReferenceException:
            logger.debug("♻️ Retrying stale element...")
        time.sleep(delay)
    return None


def safe_action(fn, name="unknown_action", retries=2, delay=2):
    """Executes an action safely with retry/backoff."""
    for attempt in range(retries):
        try:
            return fn()
        except (StaleElementReferenceException, TimeoutException) as e:
            logger.warning(f"⚠️ {type(e).__name__} during {name}, retrying...")
        except WebDriverException as e:
            logger.error(f"❌ WebDriver error during {name}: {e}")
        time.sleep(delay * (attempt + 1))
    logger.error(f"❌ Giving up {name} after {retries} retries.")
    return None


# ==========================================
# Page load waiting logic
# ==========================================

Locator = Tuple[str, str]  # (By.CSS_SELECTOR, "…") etc.


def _any_visible(driver: webdriver.Remote, locator: Locator) -> bool:
    by, value = locator
    try:
        elems = driver.find_elements(by, value)
        return any(e.is_displayed() for e in elems)
    except Exception:
        return False


def _all_visible(driver: webdriver.Remote, locators: Iterable[Locator]) -> bool:
    return all(_any_visible(driver, loc) for loc in locators)


def get_and_wait_until_loaded(
    driver: webdriver.Remote,
    url: str,
    *,
    poll: float = 0.25,
    wait_for: Optional[Locator] = None,
    wait_for_all: Optional[Iterable[Locator]] = None,
) -> None:
    """
    Opens a URL and waits until document.readyState == 'complete' and (optionally)
    specific element(s) are visible.
    """
    warn_every = 30
    timeout = 60

    driver.get(url)
    context = url
    start = time.monotonic()
    next_warn_at = start + warn_every
    deadline = start + timeout

    # Wait for document.readyState
    while True:
        now = time.monotonic()
        try:
            state = driver.execute_script("return document.readyState")
        except Exception:
            state = None

        if state == "complete":
            break

        if now >= next_warn_at:
            logger.warning(
                f"⏳ [{context}] Waiting for readyState='complete' ({now - start:.1f}s, state={state!r})"
            )
            next_warn_at += warn_every

        if now >= deadline:
            raise TimeoutError(
                f"[{context}] ❌ Page did not load after {timeout}s (last state={state!r})"
            )

        time.sleep(poll)

    # Optional: wait for visibility
    if wait_for or wait_for_all:
        next_warn_at = time.monotonic() + warn_every
        while True:
            now = time.monotonic()
            ok = (
                _any_visible(driver, wait_for)
                if wait_for
                else _all_visible(driver, wait_for_all)
            )
            detail = (
                f"locator={wait_for!r}"
                if wait_for
                else f"locators={list(wait_for_all)!r}"
            )
            if ok:
                return

            if now >= next_warn_at:
                logger.warning(
                    f"⏳ [{context}] Page loaded but waiting for visible element(s): {detail}"
                )
                next_warn_at += warn_every

            if now >= deadline:
                raise TimeoutError(
                    f"[{context}] ❌ Element(s) not visible in time: {detail}"
                )

            time.sleep(poll)
