import time
from selenium import webdriver
from bot.config import settings
from loguru import logger

def wait_until_page_loaded(driver: webdriver, context: str) -> None:
    start_time = time.time()
    warned = False

    while True:
        state: str = driver.execute_script("return document.readyState")
        if state == "complete":
            break

        elapsed = time.time() - start_time
        if not warned and elapsed > settings.WAIT_WARN_AFTER:
            logger.warning(f"[{context}] ⚠️ Page still not loaded after {settings.WAIT_WARN_AFTER} seconds.")
            warned = True

        time.sleep(0.5)
