import time
from loguru import logger
from selenium.common import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

def safe_find_element(driver, by, value, *, retries=3, delay=1):
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
