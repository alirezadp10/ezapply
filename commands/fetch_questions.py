import argparse
import time
import random

from loguru import logger
from selenium.webdriver.common.by import By

from bot.authentication import Authentication
from bot.settings import settings
from bot.db_manager import DBManager
from bot.driver_manager import DriverManager
from bot.enums import ModesEnum, JobReasonEnum
from bot.helpers import get_and_wait_until_loaded, body_has_text, click_if_exists
from bot.job_applicator import JobApplicator
from bot.logger_manager import setup_logger


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

    Authentication(driver).login(username=args.username, password=args.password)

    jobs = db.get_not_applied_jobs()
    for job in jobs:
        time.sleep(settings.DELAY_TIME + random.uniform(1, 2))
        get_and_wait_until_loaded(driver, job.url)
        if body_has_text(driver, "On-site") or body_has_text(driver, "Hybrid"):
            db.cancel_job(job.id, JobReasonEnum.WORK_TYPE_MISMATCH)
            logger.error("❌ Work type mismatch.")
            continue

        if body_has_text(driver, "No longer accepting applications"):
            db.cancel_job(job.id, JobReasonEnum.EXPIRED)
            logger.error("❌ Request has been expired.")
            continue

        if not click_if_exists(driver, By.CLASS_NAME, "jobs-apply-button", index=1):
            db.cancel_job(job.id, JobReasonEnum.APPLY_BUTTON)
            logger.error("❌ Couldn't find apply button.")
            continue

        JobApplicator(driver=driver, db=db).apply_to_job(job_id=job.id)

if __name__ == "__main__":
    main()
