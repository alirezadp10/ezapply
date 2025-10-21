import time
from selenium import webdriver
from bot.config import settings
from loguru import logger

def wait_until_page_loaded(driver: webdriver, context: str) -> None:
    start_time = time.time()
    next_warn_at = settings.WAIT_WARN_AFTER
    timeout = 60 * 5  # 5 minutes

    while True:
        state: str = driver.execute_script("return document.readyState")
        if state == "complete":
            break

        elapsed = time.time() - start_time
        if elapsed >= next_warn_at:
            logger.warning(f"[{context}] ⚠️ Page still not loaded after {next_warn_at} seconds.")
            next_warn_at += settings.WAIT_WARN_AFTER

        if elapsed > timeout:
            raise TimeoutError(f"[{context}] ❌ Page did not load after {timeout} seconds (5 minutes).")

        time.sleep(0.5)
