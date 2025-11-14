import random
import time

from selenium.webdriver.common.by import By

from bot.settings import settings


def get_children(driver, root):
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
    for attempt in range(retries + 1):
        try:
            driver.find_elements(by, selector)[index].click()
            return True
        except Exception:
            time.sleep(settings.DELAY_TIME + random.uniform(1, 2))
            if attempt == retries:
                return False
    return False
