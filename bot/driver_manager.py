from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from bot.config import settings


class DriverManager:
    @staticmethod
    def create_driver(incognito=False):
        opts = Options()

        if settings.HEADLESS:
            opts.add_argument("--headless=new")

        if incognito:
            opts.add_argument("--incognito")

        opts.page_load_strategy = "none"
        opts.add_experimental_option(
            "prefs",
            {
                "profile.managed_default_content_settings.images": 0,
            },
        )
        opts.add_argument(f"user-data-dir={settings.USER_DATA_DIR}")

        driver = webdriver.Chrome(options=opts)

        driver.maximize_window()

        return driver

    @staticmethod
    def close_driver(driver: webdriver):
        driver.quit()
