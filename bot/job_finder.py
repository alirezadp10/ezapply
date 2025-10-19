from selenium.webdriver.common.by import By
from bot.enums import WorkTypes
from bot.config import settings

class JobFinder:
    def __init__(self, driver, db):
        self.driver = driver
        self.db = db

    def build_job_url(self, keyword: str, country_id: int) -> str:
        base_url = settings.LINKEDIN_BASE_URL
        params = {
            "keywords": keyword,
            "f_TPR": f"r{settings.JOB_SEARCH_TIME_WINDOW}",
            "f_WT": WorkTypes(settings.WORK_TYPE),
            "geoId": country_id,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}/jobs/search?{query}"

    def get_easy_apply_jobs(self):
        jobs = []
        for div in self.driver.find_elements(By.CSS_SELECTOR, 'div[data-job-id]'):
            job_id_str = div.get_attribute("data-job-id")
            if not job_id_str or not job_id_str.isdigit():
                continue
            if "Easy Apply" in div.text:
                title_el = div.find_element(By.CSS_SELECTOR, '.job-card-list__title--link span[aria-hidden="true"]')
                jobs.append({'id': int(job_id_str), 'title': title_el.text.strip()})
        return jobs
