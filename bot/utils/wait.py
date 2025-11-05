import time
from typing import Iterable, Optional, Tuple
from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from bot.config import settings

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
