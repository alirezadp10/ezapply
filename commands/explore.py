from loguru import logger
from selenium.webdriver.common.by import By

from bot.driver_manager import DriverManager
from bot.db_manager import DBManager
from bot.enums import ModesEnum, ElementsEnum
from bot.helpers import (
    resolve_countries,
    resolve_keywords,
    country_value,
    has_no_results,
    click_if_exists,
    body_has_text,
    has_offsite_apply_icon,
    get_children,
)
from bot.job_finder import JobFinder
from bot.logger_manager import setup_logger
from bot.utils import wait_until_page_loaded


def main() -> None:
    driver = DriverManager.create_driver(user_data_dir="/tmp/chrome-user-data")
    db = DBManager()
    finder = JobFinder(driver, db)

    countries = resolve_countries()
    keywords = resolve_keywords()

    try:
        for country in countries:
            country_val = country_value(country)

            for keyword in keywords:
                url = finder.build_job_url(keyword, country_val)

                logger.info(
                    f"🔍 Exploring: keyword='{keyword}', country='{country}' -> {url}"
                )

                driver.get(url)
                wait_until_page_loaded(driver, url)
                driver.get(url)
                wait_until_page_loaded(driver, url)

                click_if_exists(
                    driver,
                    By.CSS_SELECTOR,
                    ElementsEnum.SIGN_IN_MODAL,
                )

                if body_has_text(driver, "Please make sure your keywords are spelled correctly"):
                    continue

                job_items = get_children(driver, driver.find_element(By.CLASS_NAME, ElementsEnum.JOB_ITEMS))

                for job_item in job_items:
                    if has_offsite_apply_icon(driver):
                        continue


                logger.debug("✅ Page has results. (Call finder logic here.)")

    except Exception as e:
        logger.exception(f"❌ Error while running in EXPLORE mode: {e}")
    finally:
        DriverManager.close_driver(driver)


if __name__ == "__main__":
    setup_logger()
    logger.info(f"🚀 Running SeleniumBot in mode: {ModesEnum.EXPLORE}")
    main()
    logger.info("🏁 Exploration finished.")
