import random
import time

from loguru import logger
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By

from bot.helpers.dom_utils import click_if_exists
from bot.helpers.page_load import get_and_wait_until_loaded
from bot.helpers.page_state import body_has_text
from bot.helpers.safe_ops import safe_action, safe_find_element
from bot.settings import settings


class AuthenticationService:
    """Handles LinkedIn login flow with retry and safety wrappers."""

    def __init__(self, driver):
        self.driver = driver

    def login(self, username: str, password: str):
        """
        Safely logs into LinkedIn.
        Handles slow loading, hidden inputs, stale elements, and redirects.
        """
        login_url = f"{settings.LINKEDIN_BASE_URL}/login"
        logger.info(f"🔐 Navigating to {login_url}")

        safe_action(lambda: get_and_wait_until_loaded(self.driver, login_url), "load_login_page")

        # --- Already logged in?
        current_url = self.driver.current_url
        if any(k in current_url for k in ("feed", "notifications", "jobs")):
            logger.info("✅ Already logged in.")
            return

        # --- Handle “sign in with another account” prompt
        clicked = click_if_exists(self.driver, By.CLASS_NAME, "signin-other-account")
        if clicked:
            logger.debug("👥 Switched to 'Sign in with another account'.")

        # --- Username field
        username_el = safe_find_element(self.driver, By.NAME, "session_key")
        if username_el and username_el.get_attribute("type") != "hidden":
            safe_action(lambda: username_el.clear(), "clear_username")
            safe_action(lambda: username_el.send_keys(username), "type_username")
            logger.debug("🧠 Username entered.")
        else:
            logger.warning("⚠️ Username input missing or hidden.")

        # --- Password field
        password_el = safe_find_element(self.driver, By.NAME, "session_password")
        if password_el:
            safe_action(lambda: password_el.clear(), "clear_password")
            safe_action(lambda: password_el.send_keys(password), "type_password")
            logger.debug("🔒 Password entered.")
        else:
            logger.warning("⚠️ Password input not found.")

        # --- Submit button
        submit_el = safe_find_element(self.driver, By.CSS_SELECTOR, '[data-litms-control-urn="login-submit"]')
        if submit_el:
            safe_action(lambda: submit_el.click(), "click_login_button")
        else:
            logger.warning("⚠️ Login button not found.")

        # --- Wait and confirm login
        time.sleep(settings.DELAY_TIME + random.uniform(1, 2))

        if self.is_logged_in():
            logger.success("✅ Login successful.")
        else:
            current_url = self.driver.current_url
            if body_has_text(self.driver, "challenge") or "checkpoint" in current_url:
                logger.warning("⚠️ Captcha or verification step detected.")
            else:
                logger.warning(f"⚠️ Login may not have completed. Current URL: {current_url}")

    def is_logged_in(self) -> bool:
        """Check whether the user appears logged in (based on current URL)."""
        try:
            url = self.driver.current_url
            return any(k in url for k in ("feed", "notifications", "jobs"))
        except WebDriverException:
            return False
