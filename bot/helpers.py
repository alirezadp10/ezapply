import os
import time
from typing import Optional, List, Union
from loguru import logger
from selenium.common import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from bot.config import settings
from bot.enums import Country, ElementsEnum, WorkTypesEnum
from contextlib import suppress
from typing import Iterable, Tuple
from selenium import webdriver


def read_test_job_ids() -> List[str]:
    raw = os.getenv("TEST_WITH", "").strip()
    return [t.strip() for t in raw.split(",") if t.strip()]


def split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def resolve_countries() -> List[str]:
    configured = split_csv(getattr(settings, "COUNTRIES", None))
    return [c.upper() for c in configured] if configured else [c.name for c in Country]


def resolve_keywords() -> List[str]:
    keywords = split_csv(getattr(settings, "KEYWORDS", None))
    if not keywords:
        logger.warning("⚠️ No KEYWORDS configured; nothing to search for.")
    return keywords


def country_value(country_name: str) -> str:
    try:
        return Country[country_name.upper()].value
    except KeyError as e:
        valid = ", ".join([c.name for c in Country])
        raise ValueError(f"Unknown country '{country_name}'. Valid: {valid}") from e


def has_no_results(driver) -> bool:
    return bool(driver.find_elements(By.CLASS_NAME, "jobs-search-no-results-banner"))


def has_expired(driver) -> bool:
    return bool(
        driver.find_elements(By.XPATH, '//*[text()="No longer accepting applications"]')
    )


def has_exhausted_limit(driver) -> bool:
    xpath = (
        "//*[text()=\"You’ve reached today's Easy Apply limit. "
        "Great effort applying today. We limit daily submissions "
        'to help ensure each application gets the right attention."]'
    )
    return bool(driver.find_elements(By.XPATH, xpath))


def parse_job_ids_from_string(raw: str) -> List[str]:
    raw = raw or os.getenv("TEST_WITH", "")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def click_if_exists(driver, by, selector, index=0):
    """
    Try to find elements and click the given index if present.
    Returns True if clicked, False if nothing to click.
    """
    elems = driver.find_elements(by, selector)
    if len(elems) > index and is_clickable(elems[index]):
        elems[index].click()
        return True
    return False


def body_has_text(driver, text: str) -> bool:
    """
    Returns True if the given text is present in the <body>, else False.
    """
    body = driver.find_element(By.TAG_NAME, "body")
    return text in body.text


def has_offsite_apply_icon(driver) -> bool:
    """
    Returns True if the page has the offsite apply icon, else False.
    """
    elems = driver.find_elements(By.CSS_SELECTOR, ElementsEnum.OFFSITE_APPLY_ICON)
    return len(elems) > 0


def get_children(
    driver,
    root: Optional[Union[WebElement, tuple]] = None,
    by: By = By.XPATH,
    value: str = "",
) -> List[WebElement]:
    """
    Return direct children of an element.

    - If `root` is a WebElement → get its children.
    - If `root` is a locator tuple like (By.CLASS_NAME, "foo") → find first and get its children.
    - If `root` is None → use <body>.

    Example:
        get_children(driver, (By.CLASS_NAME, "jobs-search__results-list"))
        get_children(driver, some_elem)
    """
    # 1) decide the root element
    if root is None:
        root_el = driver.find_element(By.TAG_NAME, "body")
    elif isinstance(root, tuple):
        by_loc, val = root
        root_el = driver.find_element(by_loc, val)
    else:
        root_el = root  # already a WebElement

    # 2) now get its direct children
    return root_el.find_elements(By.XPATH, "./*")


def is_clickable(element):
    return element.is_displayed() and element.is_enabled()


def click_with_rate_limit_checking(driver, job_item, delay=2):
    def snapshot_count():
        return len(getattr(driver, "requests", []))

    def has_new_rate_limit_since(index):
        requests = getattr(driver, "requests", [])[index:]
        for req in requests:
            resp = getattr(req, "response", None)
            if not resp:
                continue
            status = getattr(resp, "status_code", None) or getattr(resp, "status", None)
            if status == 429:
                return True
        return False

    if is_clickable(job_item):
        snap = snapshot_count()

        with suppress(Exception):
            job_item.click()

        time.sleep(delay)

        if not has_new_rate_limit_since(snap):
            return True

        time.sleep(delay * 2)

    return False


def build_job_url(
    keyword: Optional[str] = None,
    country_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> str:
    base_url = settings.LINKEDIN_BASE_URL

    if job_id is not None:
        return f"{base_url}/jobs/search?currentJobId={job_id}"

    params = {}

    if keyword:
        quoted_keyword = f'"{keyword.strip()}"'
        params["keywords"] = quoted_keyword

    if country_id:
        params["geoId"] = country_id

    params["f_TPR"] = f"r{settings.JOB_SEARCH_TIME_WINDOW}"
    params["f_WT"] = WorkTypesEnum(settings.WORK_TYPE)

    query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)

    return f"{base_url}/jobs/search?{query}"


def safe_find_element(driver, by, value, *, retries=3, delay=1):
    """Find element safely with retries."""
    for attempt in range(retries):
        try:
            return driver.find_element(by, value)
        except NoSuchElementException:
            if attempt == retries - 1:
                logger.warning(f"⚠️ Element not found: {value}")
            time.sleep(delay)
        except StaleElementReferenceException:
            logger.debug("♻️ Retrying stale element...")
            time.sleep(delay)
    return None


def safe_action(fn, name="unknown_action", retries=2, delay=2):
    """Executes an action safely with retry/backoff."""
    for attempt in range(retries):
        try:
            return fn()
        except StaleElementReferenceException:
            logger.warning(f"⚠️ Stale element during {name}, retrying...")
        except TimeoutException:
            logger.warning(f"⏱ Timeout during {name}, retrying...")
        except WebDriverException as e:
            logger.error(f"❌ WebDriver error during {name}: {e}")
        time.sleep(delay * (attempt + 1))
    logger.error(f"❌ Giving up {name} after {retries} retries.")
    return None


Locator = Tuple[str, str]  # (By.CSS_SELECTOR, "…") etc.


def _any_visible(driver: webdriver.Remote, locator: Locator) -> bool:
    by, value = locator
    try:
        elems = driver.find_elements(by, value)
        for el in elems:
            try:
                if el.is_displayed():
                    return True
            except StaleElementReferenceException:
                # element went stale between find and check; ignore and continue
                continue
        return False
    except Exception:
        # e.g., invalid selector or transient driver error; treat as not visible this tick
        return False


def _all_visible(driver: webdriver.Remote, locators: Iterable[Locator]) -> bool:
    return all(_any_visible(driver, loc) for loc in locators)


def get_and_wait_until_loaded(
    driver: webdriver.Remote,
    url: str,
    *,
    poll: float = 0.25,  # how often to check (seconds)
    warn_every: Optional[float] = None,  # falls back to settings.WAIT_WARN_AFTER
    wait_for: Optional[
        tuple[str, str]
    ] = None,  # wait until ANY element matching this locator is visible
    wait_for_all: Optional[
        Iterable[tuple[str, str]]
    ] = None,  # wait until ALL locators are visible
) -> None:
    """
    Opens a URL with driver.get() and waits until:
    1. document.readyState == 'complete'
    2. (optionally) specific element(s) are visible.

    Args:
        driver: Selenium WebDriver.
        url: URL to open.
        poll: Poll interval.
        warn_every: Log a warning every N seconds while waiting.
        wait_for: A single locator (By, value) that must become visible.
        wait_for_all: A list/tuple of locators that must all be visible.

    Raises:
        TimeoutError: If conditions aren't met within timeout.
    """
    if warn_every is None:
        warn_every = getattr(settings, "WAIT_WARN_AFTER", 30.0)

    # === Phase 0: navigate ===
    driver.get(url)
    context = url

    start = time.monotonic()
    next_warn_at = start + warn_every
    deadline = start + getattr(settings, "TIMEOUT", 60.0)

    # === Phase 1: wait for readyState ===
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
                f"⏳ [{context}] Still waiting for document.readyState='complete' after {now - start:.1f}s (state={state!r})."
            )
            next_warn_at += warn_every

        if now >= deadline:
            raise TimeoutError(
                f"[{context}] ❌ Page did not load after {now - start:.1f}s (timeout {settings.TIMEOUT}s). Last readyState={state!r}."
            )

        time.sleep(poll)

    # === Phase 2 (optional): element visibility ===
    if wait_for is None and wait_for_all is None:
        return  # nothing else to wait for

    next_warn_at = time.monotonic() + warn_every

    def _any_visible(driver, locator):
        by, value = locator
        try:
            elements = driver.find_elements(by, value)
            return any(e.is_displayed() for e in elements)
        except Exception:
            return False

    def _all_visible(driver, locators):
        return all(_any_visible(driver, loc) for loc in locators)

    while True:
        now = time.monotonic()

        ok = False
        detail = ""
        if wait_for is not None:
            ok = _any_visible(driver, wait_for)
            detail = f"locator={wait_for!r}"
        elif wait_for_all is not None:
            ok = _all_visible(driver, wait_for_all)
            detail = f"locators={list(wait_for_all)!r}"

        if ok:
            return

        if now >= next_warn_at:
            elapsed = now - start
            logger.warning(
                f"⏳ [{context}] Page loaded but waiting for visible element(s): {detail} (elapsed {elapsed:.1f}s)."
            )
            next_warn_at += warn_every

        if now >= deadline:
            raise TimeoutError(
                f"[{context}] ❌ Element(s) not visible in time: {detail} (timeout {settings.TIMEOUT}s)."
            )

        time.sleep(poll)
