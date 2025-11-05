import os
import time
from typing import Optional, List, Union
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from bot.config import settings
from bot.enums import Country, ElementsEnum
from contextlib import suppress


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


# --- DOM helpers ---
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
    elems = driver.find_elements(By.CSS_SELECTOR, ElementsEnum.OFFSITE_APPLY_SELECTOR)
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
        """Return how many requests have been captured so far."""
        return len(getattr(driver, "requests", []))

    def has_new_rate_limit_since(index):
        """Return True if a *new* 429 appeared after snapshot index."""
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
