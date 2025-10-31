import time
from loguru import logger
from selenium.webdriver.common.by import By
from bot.config import settings
from bot.helpers import has_expired
from bot.utils import wait_until_page_loaded

def run_test_jobs(bot, job_ids):
    for job_id in job_ids:
        try:
            url = bot.finder.build_job_url(job_id=job_id)
            bot.driver.get(url)
            time.sleep(settings.DELAY_TIME)
            if has_expired(bot.driver):
                continue
            wait_until_page_loaded(bot.driver, url, wait_for=(By.ID, "jobs-apply-button-id"))
            bot.applicator.apply_to_job(job_id)
        except Exception as e:
            logger.error(f"❌ Error applying to job #{job_id}: {e}")
