import time
from loguru import logger
from selenium.webdriver.common.by import By
from bot.config import settings
from bot.ai_service import AIService
from bot.form_parser import FormParser
from bot.form_filler import FormFiller

class JobApplicator:
    def __init__(self, driver, db):
        self.driver = driver
        self.db = db
        self.parser = FormParser(driver)
        self.filler = FormFiller(driver)

    def apply_to_job(self, job):
        job_id = job['id']
        logger.info(f"🟩 Applying to job {job_id}")
        self.driver.find_element(By.CSS_SELECTOR, f'div[data-job-id="{job_id}"]').click()
        time.sleep(settings.DELAY_TIME)
        self.driver.find_element(By.ID, "jobs-apply-button-id").click()
        time.sleep(settings.DELAY_TIME)

        while True:
            payload = self.parser.parse_form_fields()

            if payload:
                answers = AIService.ask_form_answers(payload)
                self.filler.fill_fields(payload, answers)

            if self._submit_if_ready(job_id):
                break

            if self._next_step():
                continue

    def _next_step(self):
        return self._click_if_exists('[aria-label="Continue to next step"]') or \
            self._click_if_exists('[aria-label="Review your application"]')

    def _submit_if_ready(self, job_id):
        if self._click_if_exists('[aria-label="Submit application"]'):
            logger.info(f"✅ Job {job_id} submitted.")
            self._click_if_exists('[aria-label="Dismiss"]')
            time.sleep(settings.DELAY_TIME)
            return True
        return False

    def _click_if_exists(self, selector):
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, selector)
            el.click()
            time.sleep(settings.DELAY_TIME)
            return True
        except Exception:
            return False
