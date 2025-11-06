import argparse
import time
import random

from loguru import logger

from bot.authentication import Authentication
from bot.config import settings
from bot.db_manager import DBManager
from bot.driver_manager import DriverManager
from bot.enums import ModesEnum
from bot.helpers import get_and_wait_until_loaded
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
        print(job.job_id)


if __name__ == "__main__":
    main()
