import argparse
import random
import time

from loguru import logger
from selenium.webdriver.common.by import By

from bot.db_manager import DBManager
from bot.driver_manager import DriverManager
from bot.enums import JobStatusEnum
from bot.helpers.dom_utils import click_if_exists
from bot.helpers.page_load import get_and_wait_until_loaded
from bot.helpers.page_state import body_has_text
from bot.logger_manager import setup_logger
from bot.services import AuthenticationService, JobApplicatorService
from bot.settings import settings


def parse_args():
    parser = argparse.ArgumentParser(description="Run Selenium LinkedIn Bot")
    parser.add_argument("--username", "-u", required=True, help="LinkedIn username")
    parser.add_argument("--password", "-p", required=True, help="LinkedIn password")
    parser.add_argument("--without_submit", "-f", action="store_true", help="Just gather the questions")
    return parser.parse_args()


def main():
    setup_logger()
    args = parse_args()

    logger.info("🚀 Running SeleniumBot in mode: apply")

    db = DBManager()

    driver = DriverManager.create_driver(profile=args.username)

    AuthenticationService(driver).login(username=args.username, password=args.password)

    jobs = db.job.get_not_applied() if args.without_submit else db.job.get_ready_for_apply()

    for job in jobs:
        try:
            get_and_wait_until_loaded(driver, job.url)
            time.sleep(settings.DELAY_TIME + random.uniform(1, 2))

            # --- WORK TYPE CHECK ----
            if body_has_text(driver, "On-site") or body_has_text(driver, "Hybrid"):
                db.job.update_status(job.id, JobStatusEnum.WORK_TYPE_MISMATCH)
                logger.error(f"❌ Work type mismatch. #{job.id}")
                continue

            if body_has_text(driver, "No longer accepting applications"):
                db.job.update_status(job.id, JobStatusEnum.EXPIRED)
                logger.error(f"❌ Request has been expired. #{job.id}")
                continue

            # --- APPLY BUTTON ----
            if not click_if_exists(driver, By.CLASS_NAME, "jobs-apply-button", index=1, retries=5):
                db.job.update_status(job.id, JobStatusEnum.APPLY_BUTTON)
                logger.error(f"❌ Couldn't find apply button. #{job.id}")
                continue

            if body_has_text(driver, "Job search safety reminder"):
                driver.find_element(By.CSS_SELECTOR, "[data-live-test-job-apply-button]").click()

            logger.info(f"🔎 Processing job #{job.id}")

            applicator = JobApplicatorService(driver=driver, db=db)
            applicator.run(job=job, submit=not args.without_submit)
        except Exception as ex:
            logger.error(f"❌ error: {ex}")

    db.close()


if __name__ == "__main__":
    main()
