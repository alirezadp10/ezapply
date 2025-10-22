import os
import time
from loguru import logger
from selenium.webdriver.common.by import By
from bot.db_manager import DBManager
from bot.config import settings
from bot.enums import Country
from bot.driver_manager import DriverManager
from bot.linkedin_auth import LinkedInAuth
from bot.job_finder import JobFinder
from bot.job_applicator import JobApplicator
from bot.utils import wait_until_page_loaded


class SeleniumBot:
    def __init__(self, name: str, db_url: str):
        self.name = name
        self.driver = DriverManager.create_driver()
        self.db = DBManager(db_url)
        self.auth = LinkedInAuth(self.driver)
        self.finder = JobFinder(self.driver, self.db)
        self.applicator = JobApplicator(self.driver, self.db)

    def run(self):
        logger.info("Ensuring login state...")
        self.auth.login_if_needed()

        if os.getenv('TEST_WITH'):
            url = self.finder.build_job_url(job_id=int(os.getenv('TEST_WITH')))
            self.driver.get(url)
            wait_until_page_loaded(self.driver, url, wait_for=(By.ID, "jobs-apply-button-id"))
            self.applicator.apply_to_job(int(os.getenv('TEST_WITH')))
            return

        countries = (
            [c.strip().upper() for c in settings.COUNTRIES.split(",") if c.strip()]
            if settings.COUNTRIES else [c.name for c in Country]
        )

        keywords = [k.strip() for k in settings.KEYWORDS.split(",") if k.strip()]

        for country in countries:
            for keyword in keywords:
                self._process_country_keyword(country, keyword)

    def _process_country_keyword(self, country, keyword):
        url = self.finder.build_job_url(keyword, Country[country].value)
        self.driver.get(url)
        wait_until_page_loaded(self.driver, url)

        if self._has_no_results():
            return

        jobs = self.finder.get_easy_apply_jobs()

        for job in jobs:
            if self.db.is_applied_for_job(job['id']):
                continue
            try:
                self.driver.get(self.finder.build_job_url(job_id=job['id']))
                wait_until_page_loaded(self.driver, f'div[data-job-id="{job["id"]}"]', wait_for=(By.ID, "jobs-apply-button-id"))
                self.applicator.apply_to_job(job['id'])
                self.db.save_job(
                    title=job['title'],
                    job_id=job['id'],
                    status="applied",
                    url=f"{url}&currentJobId={job['id']}"
                )
            except Exception as e:
                logger.error(f"❌ Error applying to job {job['id']}: {e}")
                self.db.save_job(
                    title=job['title'],
                    job_id=job['id'],
                    status="failed",
                    url=f"{url}&currentJobId={job['id']}",
                    reason=str(e)
                )

    def _has_no_results(self) -> bool:
        no_results = self.driver.find_elements(By.CLASS_NAME, 'jobs-search-no-results-banner')
        return bool(no_results)