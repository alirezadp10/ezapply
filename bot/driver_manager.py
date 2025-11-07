import re
from typing import Optional
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from bot.settings import settings
import undetected_chromedriver as uc


class DriverManager:
    @staticmethod
    def create_driver(profile: Optional[str] = None, incognito: bool = False):
        opts = Options()

        # --- Headless mode (modern flag) ---
        if settings.HEADLESS:
            opts.add_argument("--headless=new")
            opts.add_argument("--window-size=1920,1080")

        # --- Optional incognito ---
        if incognito:
            opts.add_argument("--incognito")

        # --- User profile directory setup ---
        normalized_profile = DriverManager._normalize_profile_name(profile)
        base_dir = Path(__file__).resolve().parent.parent / "profiles"
        profile_dir = base_dir / normalized_profile if normalized_profile else Path(settings.USER_DATA_DIR)
        profile_dir.mkdir(parents=True, exist_ok=True)

        # --- Create driver ---
        driver = uc.Chrome(options=opts, user_data_dir=profile_dir)
        driver.maximize_window()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
        })
        return driver

    @staticmethod
    def close_driver(driver: webdriver.Chrome) -> None:
        """Safely close the browser."""
        try:
            driver.quit()
        except Exception:
            pass

    @staticmethod
    def _normalize_profile_name(value: Optional[str]) -> Optional[str]:
        """Normalize a profile name by keeping only alphabetical characters."""
        if not value:
            return None
        value = value.strip()
        normalized = re.sub(r"[^A-Za-z]", "", value)
        return normalized or None
