import argparse
import random
import time

from loguru import logger
from selenium.webdriver.common.by import By

from bot.db_manager import DBManager
from bot.driver_manager import DriverManager
from bot.enums import JobStatusEnum, ModesEnum
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
    return parser.parse_args()


def main():
    setup_logger()
    args = parse_args()

    logger.info(f"🚀 Running SeleniumBot in mode: {ModesEnum.FETCH_QUESTIONS}")
    driver = DriverManager.create_driver(profile=args.username)
    db = DBManager()

    AuthenticationService(driver).login(username=args.username, password=args.password)

    jobs = db.get_not_applied_jobs()
    for job in jobs:
        get_and_wait_until_loaded(driver, job.url)
        time.sleep(settings.DELAY_TIME + random.uniform(1, 2))

        if body_has_text(driver, "On-site") or body_has_text(driver, "Hybrid"):
            db.update_job_status(job.id, JobStatusEnum.WORK_TYPE_MISMATCH)
            logger.error("❌ Work type mismatch.")
            continue

        if body_has_text(driver, "No longer accepting applications"):
            db.update_job_status(job.id, JobStatusEnum.EXPIRED)
            logger.error("❌ Request has been expired.")
            continue

        if not click_if_exists(driver, By.CLASS_NAME, "jobs-apply-button", index=1, retries=5):
            db.update_job_status(job.id, JobStatusEnum.APPLY_BUTTON)
            logger.error("❌ Couldn't find apply button.")
            continue

        if body_has_text(driver, "Job search safety reminder"):
            driver.find_element(By.CSS_SELECTOR, "[data-live-test-job-apply-button]").click()

        logger.info(f"🔎 Processing job #{job.id}")
        JobApplicatorService(driver=driver, db=db).apply_to_job(job_id=job.id)


if __name__ == "__main__":
    main()
