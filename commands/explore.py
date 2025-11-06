import time
import random
from loguru import logger
from selenium.common.exceptions import TimeoutException
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
    safe_action,
    safe_find_element,
)
from bot.logger_manager import setup_logger
from bot.utils.wait import get_and_wait_until_loaded


def explore_jobs(driver, db, countries, keywords):
    """Explore job listings for all countries and keywords."""
    for country in countries:
        country_val = country_value(country)
        for keyword in keywords:
            try:
                logger.info(f"🔍 Exploring: keyword='{keyword}', country='{country}'")
                url = build_job_url(keyword, country_val)
                process_page(driver, db, url, country, keyword)
            except Exception as e:
                logger.exception(f"💥 Failed to process {keyword=} {country=}: {e}")
                time.sleep(random.uniform(3, 6))  # small cooldown


def process_page(driver, db, url, country, keyword):
    """Processes a single job results page safely."""
    for attempt in range(3):
        try:
            get_and_wait_until_loaded(driver, url)
            click_if_exists(driver, By.CSS_SELECTOR, ElementsEnum.sign_in_modal)
            time.sleep(2)
        except TimeoutException:
            logger.warning(f"⚠️ Timeout loading {url}, retrying...")

    if body_has_text(driver, "Please make sure your keywords are spelled correctly"):
        logger.info("🔎 No results found for this search.")
        return

    container = safe_find_element(driver, By.CLASS_NAME, ElementsEnum.job_items)
    if not container:
        logger.warning("⚠️ No job container found.")
        return

    job_items = get_children(driver, container)
    if not job_items:
        logger.info("ℹ️ No job items found on this page.")
        return

    for job_item in job_items:
        safe_action(
            lambda: process_job_item(driver, db, job_item, country, keyword),
            name="process_job_item",
        )


def process_job_item(driver, db, job_item, country, keyword):
    """Safely process a single job card."""
    click_if_exists(driver, By.CSS_SELECTOR, ElementsEnum.sign_in_modal)

    if not click_with_rate_limit_checking(driver, job_item):
        logger.debug("⏳ Skipped job due to rate limit or click failure.")
        return

    if has_offsite_apply_icon(driver):
        logger.info("🔗 Skipped offsite application.")
        return

    active_card = safe_find_element(driver, By.CLASS_NAME, ElementsEnum.job_card_active)
    if not active_card:
        return

    try:
        urn = active_card.get_attribute("data-entity-urn") or ""
        job_id = urn.rsplit(":", 1)[-1]
        a_tag = active_card.find_element(By.TAG_NAME, "a")
        title = a_tag.text.strip()
        link = a_tag.get_attribute("href")
    except Exception as e:
        logger.warning(f"⚠️ Failed extracting job metadata: {e}")
        return

    desc_elem = safe_find_element(driver, By.CLASS_NAME, ElementsEnum.job_description)
    description = desc_elem.get_attribute("innerText") if desc_elem else ""

    try:
        db.save_job(
            job_id=job_id,
            title=title,
            description=description,
            country=country,
            keyword=keyword,
            url=link,
        )
        logger.success(f"✅ Saved job: #{job_id} '{title}' ({country}, {keyword})")
    except Exception as e:
        logger.exception(f"💾 Failed saving job {job_id}: {e}")


def main():
    setup_logger()
    logger.info(f"🚀 Running SeleniumBot in mode: {ModesEnum.EXPLORE}")
    driver = DriverManager.create_driver(incognito=True)
    db = DBManager()

    countries = resolve_countries()
    keywords = resolve_keywords()

    try:
        explore_jobs(driver, db, countries, keywords)
        logger.info("🏁 Exploration completed successfully.")
    except Exception as e:
        logger.exception(f"❌ Critical failure in main loop: {e}")
    finally:
        safe_action(lambda: DriverManager.close_driver(driver), name="close_driver")


if __name__ == "__main__":
    main()
