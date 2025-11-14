# bot/helpers/page_load.py

import time
from typing import Iterable, Optional, Tuple

from loguru import logger
from selenium import webdriver

Locator = Tuple[str, str]

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

    warn_every = 30
    timeout = 60

    driver.get(url)
    start = time.monotonic()
    context = url
    next_warn_at = start + warn_every
    deadline = start + timeout

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
                f"⏳ [{context}] Waiting for readyState='complete' "
                f"({now - start:.1f}s, state={state!r})"
            )
            next_warn_at += warn_every

        if now >= deadline:
            raise TimeoutError(
                f"[{context}] ❌ Page did not load after {timeout}s (last state={state!r})"
            )

        time.sleep(poll)

    # Waiting for visibility
    next_warn_at = time.monotonic() + warn_every
    if wait_for or wait_for_all:
        while True:
            now = time.monotonic()

            ok = (
                _any_visible(driver, wait_for)
                if wait_for
                else _all_visible(driver, wait_for_all)
            )

            if ok:
                return

            if now >= next_warn_at:
                detail = (
                    f"locator={wait_for!r}"
                    if wait_for
                    else f"locators={list(wait_for_all)!r}"
                )
                logger.warning(
                    f"⏳ [{context}] Page loaded but waiting for visible element(s): {detail}"
                )
                next_warn_at += warn_every

            if now >= deadline:
                detail = (
                    f"locator={wait_for!r}"
                    if wait_for
                    else f"locators={list(wait_for_all)!r}"
                )
                raise TimeoutError(
                    f"[{context}] ❌ Element(s) not visible in time: {detail}"
                )

            time.sleep(poll)
