import time
from typing import Optional

from loguru import logger
from selenium.webdriver.common.by import By
from bot.enums import WorkTypesEnum, ElementsEnum
from bot.config import settings

class JobFinder:
    def __init__(self, driver, db):
        self.driver = driver
        self.db = db

    def build_job_url(self, keyword: Optional[str] = None, country_id: Optional[str] = None, job_id: Optional[str] = None) -> str:
        base_url = settings.LINKEDIN_BASE_URL

        if job_id is not None:
            return f"{base_url}/jobs/search?currentJobId={job_id}"

        params = {}

        if keyword:
            quoted_keyword = f'"{keyword.strip()}"'
            params["keywords"] = quoted_keyword

        if country_id:
            params["geoId"] = country_id

        params["f_TPR"] = f"r{settings.JOB_SEARCH_TIME_WINDOW}"
        params["f_WT"] = WorkTypesEnum(settings.WORK_TYPE)

        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)

        return f"{base_url}/jobs/search?{query}"

    def get_easy_apply_jobs(self):
        jobs = []
        time.sleep(settings.DELAY_TIME)
        for div in self.driver.find_elements(By.CSS_SELECTOR, ElementsEnum.JOB_ID):
            job_id = div.get_attribute("data-job-id")
            if "Easy Apply" in div.text:
                job_title = div.find_elements(By.CSS_SELECTOR, ElementsEnum.JOB_TITLE)
                if not job_title:
                    logger.error(f"❌ Could not find job title for #{job_id}")
                    continue
                jobs.append({'id': job_id, 'title': job_title[0].text.strip()})
        return jobs
