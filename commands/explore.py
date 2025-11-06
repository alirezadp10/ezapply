import time
from loguru import logger
from selenium.webdriver.common.by import By

from bot.driver_manager import DriverManager
from bot.db_manager import DBManager
from bot.enums import ModesEnum, ElementsEnum
from bot.helpers import (
    resolve_countries,
    resolve_keywords,
    country_value,
    click_if_exists,
    body_has_text,
    has_offsite_apply_icon,
    get_children,
    click_with_rate_limit_checking,
    build_job_url,
)
from bot.logger_manager import setup_logger
from bot.utils.wait import get_and_wait_until_loaded


def explore_jobs(driver, db, countries, keywords):
    """Explores job listings by country and keyword."""
    for country in countries:
        country_val = country_value(country)
        for keyword in keywords:
            logger.info(f"🔍 Exploring: keyword='{keyword}', country='{country}'")
            url = build_job_url(keyword, country_val)
            process_page(driver, db, url)


def process_page(driver, db, url):
    """Processes a single job page."""
    for i in range(3):
        get_and_wait_until_loaded(driver, url)
        click_if_exists(driver, By.CSS_SELECTOR, ElementsEnum.sign_in_modal)
        time.sleep(3)

    if body_has_text(driver, "Please make sure your keywords are spelled correctly"):
        return

    job_items = get_children(
        driver, driver.find_element(By.CLASS_NAME, ElementsEnum.job_items)
    )

    for job_item in job_items:
        process_job_item(driver, db, job_item)


def process_job_item(driver, db, job_item):
    """Processes a single job item."""
    click_if_exists(driver, By.CSS_SELECTOR, ElementsEnum.sign_in_modal)

    if not click_with_rate_limit_checking(driver, job_item):
        return

    if has_offsite_apply_icon(driver):
        return

    job_id = (
        driver.find_element(By.CLASS_NAME, ElementsEnum.job_card_active)
        .get_attribute("data-entity-urn")
        .rsplit(":", 1)[-1]
    )
    title = (
        driver.find_element(By.CLASS_NAME, ElementsEnum.job_card_active)
        .find_element(By.TAG_NAME, "a")
        .text
    )
    link = (
        driver.find_element(By.CLASS_NAME, ElementsEnum.job_card_active)
        .find_element(By.TAG_NAME, "a")
        .get_attribute("href")
    )
    description = driver.find_element(By.CLASS_NAME, ElementsEnum.job_description).text

    db.save_job(job_id=job_id, title=title, description=description, link=link)


def main() -> None:
    driver = DriverManager.create_driver(incognito=True)
    db = DBManager()

    countries = resolve_countries()
    keywords = resolve_keywords()

    try:
        explore_jobs(driver, db, countries, keywords)
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
