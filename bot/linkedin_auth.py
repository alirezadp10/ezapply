import time
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bot.config import settings

class LinkedInAuth:
    def __init__(self, driver):
        self.driver = driver

    def login_if_needed(self):
        self.driver.get(f"{settings.LINKEDIN_BASE_URL}/login/fa")
        time.sleep(settings.DELAY_TIME)

        if any(keyword in self.driver.current_url for keyword in ("feed", "notifications")):
            logger.info("✅ Already logged in.")
            return

        self.driver.find_element(By.NAME, "session_key").send_keys(settings.LINKEDIN_USERNAME)
        self.driver.find_element(By.NAME, "session_password").send_keys(settings.LINKEDIN_PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, '[data-litms-control-urn="login-submit"]').click()

        WebDriverWait(self.driver, settings.DELAY_TIME).until(EC.url_contains("feed"))
        logger.info("✅ Login successful.")
