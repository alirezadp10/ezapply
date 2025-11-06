import re
from typing import Optional
from pathlib import Path
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options

from bot.config import settings


class DriverManager:
    @staticmethod
    def create_driver(profile: Optional[str] = None, incognito: bool = False):
        opts = Options()

        if settings.HEADLESS:
            opts.add_argument("--headless=new")

        if incognito:
            opts.add_argument("--incognito")

        opts.page_load_strategy = "none"
        opts.add_experimental_option(
            "prefs",
            {"profile.managed_default_content_settings.images": 0},
        )

        normalized_profile = DriverManager._normalize_profile_name(profile)

        # ✅ Store profiles under project directory
        base_dir = Path(__file__).resolve().parent.parent / "profiles"
        profile_dir = base_dir / normalized_profile if normalized_profile else Path(settings.USER_DATA_DIR)

        # Create directory if missing
        profile_dir.mkdir(parents=True, exist_ok=True)

        print(f"✅ Using profile dir: {profile_dir}")
        opts.add_argument(f"user-data-dir={profile_dir}")

        driver = webdriver.Chrome(options=opts)
        driver.maximize_window()
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
