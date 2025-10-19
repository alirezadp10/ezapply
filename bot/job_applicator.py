import time

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bot.ai_service import AIService
from bot.config import settings
from bot.form_parser import FormParser
from bot.form_filler import FormFiller

class JobApplicator:
    def __init__(self, driver, db):
        self.driver = driver
        self.db = db
        self.parser = FormParser(driver)
        self.filler = FormFiller(driver)

    def apply_to_job(self, job_id: int):
        if self.driver.find_elements(By.CSS_SELECTOR, f'div[data-job-id="{job_id}"]'):
            self.driver.find_element(By.CSS_SELECTOR, f'div[data-job-id="{job_id}"]').click()

        try:
            logger.info(f"yuhoooooo")
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.ID, "jobs-apply-button-id"))
            ).click()
            time.sleep(settings.DELAY_TIME)
        except Exception as e:
            logger.error("couldn't find the element.")
            raise e


        while True:
            payload = self.parser.parse_form_fields()

            if payload:
                answers = AIService.ask_form_answers(payload)
                self.filler.fill_fields(payload, answers)

            if self.driver.find_elements(By.CSS_SELECTOR, '[type="error-pebble-icon"]'):
                self._close_and_next()
                raise Exception("couldn't fill out the form.")

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

    def _close_and_next(self):
        self._click_if_exists('[aria-label="Dismiss"]')
        self._click_if_exists('[data-control-name="discard_application_confirm_btn"]')
