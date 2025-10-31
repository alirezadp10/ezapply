from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bot.config import settings

class DriverManager:
    @staticmethod
    def create_driver(user_data_dir: str):
        opts = Options()

        if settings.HEADLESS:
            opts.add_argument("--headless=new")

        opts.page_load_strategy = "none"
        opts.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 0,
        })
        opts.add_argument(f"user-data-dir={user_data_dir}")

        return webdriver.Chrome(options=opts)

    @staticmethod
    def close_driver(driver: webdriver):
        driver.quit()