import os
import time
from typing import Iterable, List, Dict, Any, Optional

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
    """
    High-level orchestration of the LinkedIn Easy Apply workflow.

    Responsibilities:
      - Ensure authenticated session
      - Resolve search space (countries x keywords)
      - Visit search results, collect "Easy Apply" jobs
      - Apply to each eligible job and persist outcome
    """

    def __init__(self, name: str, db_url: str) -> None:
        self.name = name
        self.driver = DriverManager.create_driver()
        self.db = DBManager(db_url)
        self.auth = LinkedInAuth(self.driver)
        self.finder = JobFinder(self.driver, self.db)
        self.applicator = JobApplicator(self.driver, self.db)

    # -------------------------
    # Public API
    # -------------------------
    def run(self) -> None:
        logger.info("ℹ️ Ensuring login state…")
        self.auth.login_if_needed()

        # Optional: run against specific job IDs for debugging
        test_ids = self._read_test_job_ids()
        if test_ids:
            self._run_test_jobs(test_ids)
            return

        countries = self._resolve_countries()
        keywords = self._resolve_keywords()

        for country in countries:
            for keyword in keywords:
                self._process_country_keyword(country, keyword)

    # -------------------------
    # Orchestration helpers
    # -------------------------
    def _run_test_jobs(self, job_ids: Iterable[str]) -> None:
        for job_id in job_ids:
            try:
                url = self.finder.build_job_url(job_id=job_id)
                self.driver.get(url)
                time.sleep(settings.DELAY_TIME)
                if self._has_expired():
                    continue
                wait_until_page_loaded(self.driver, url, wait_for=(By.ID, "jobs-apply-button-id"))
                self.applicator.apply_to_job(job_id)
            except Exception as e:
                logger.error(f"❌ Error applying to job #{job_id}: {e}")

    def _process_country_keyword(self, country: str, keyword: str) -> None:
        """
        Visit a country+keyword search page, enumerate Easy Apply jobs,
        and attempt applications for jobs not yet applied.
        """
        country_value = self._country_value(country)
        url = self.finder.build_job_url(keyword, country_value)

        self.driver.get(url)
        wait_until_page_loaded(self.driver, url)

        if self._has_no_results():
            logger.info(f"ℹ️ No results for '{keyword}' in '{country}'. Skipping.")
            return

        jobs = self._safe_get_easy_apply_jobs()
        if not jobs:
            logger.info(f"ℹ️ No easy-apply jobs found for '{keyword}' in '{country}'.")
            return

        for job in jobs:
            if self.db.is_applied_for_job(job['id']):
                logger.info(f"ℹ️ Already applied to job #{job['id']}, skipping.")
                continue

            job_url = self.finder.build_job_url(job_id=job['id'])
            try:
                self.driver.get(job_url)
                time.sleep(settings.DELAY_TIME)
                if self._has_expired():
                    continue
                if self._has_exhausted_limitation():
                    logger.error("❌ Daily application limit reached. Stopping further applications for today.")
                    continue

                wait_until_page_loaded(
                    self.driver,
                    f'div[data-job-id="{job["id"]}"]',
                    wait_for=(By.ID, "jobs-apply-button-id"),
                )
                self.applicator.apply_to_job(job['id'])
                self._save_job_result(job, status="applied", base_url=url)
                logger.success(f"✅ Applied to job #{job['id']}: {job.get('title', '(no title)')}")
            except Exception as e:
                logger.error(f"❌ Error applying to job #{job['id']}: {e}")
                self._save_job_result(job, status="failed", base_url=url, reason=str(e))

    # -------------------------
    # Data access helpers
    # -------------------------
    def _safe_get_easy_apply_jobs(self) -> List[Dict[str, Any]]:
        """
        Wraps finder.get_easy_apply_jobs to ensure we always get a list.
        """
        try:
            jobs = self.finder.get_easy_apply_jobs() or []
            # normalize shape
            normalized = []
            for j in jobs:
                if "id" not in j:
                    continue
                normalized.append({
                    "id": j["id"],
                    "title": j.get("title") or "",
                })
            return normalized
        except Exception as e:
            logger.error(f"❌ Failed to fetch Easy Apply jobs: {e}")
            return []

    def _save_job_result(
            self,
            job: Dict[str, Any],
            *,
            status: str,
            base_url: str,
            reason: Optional[str] = None,
    ) -> None:
        job_id = job["id"]
        title = job.get("title") or ""
        job_url_with_context = f"{base_url}&currentJobId={job_id}"
        self.db.save_job(
            title=title,
            job_id=job_id,
            status=status,
            url=job_url_with_context,
            reason=reason,
        )

    # -------------------------
    # Config helpers
    # -------------------------
    @staticmethod
    def _read_test_job_ids() -> List[str]:
        raw = os.getenv("TEST_WITH", "").strip()
        if not raw:
            return []
        ids: List[str] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                ids.append(token)
            except ValueError:
                logger.warning(f"⚠️ Ignoring invalid TEST_WITH id: {token}")
        return ids

    @staticmethod
    def _split_csv(value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [part.strip() for part in value.split(",") if part.strip()]

    def _resolve_countries(self) -> List[str]:
        """
        Determine the list of countries to use. Returns UPPERCASE enum names
        compatible with Country[<NAME>].
        """
        configured = self._split_csv(getattr(settings, "COUNTRIES", None))
        if configured:
            return [c.upper() for c in configured]
        # default: all enum names
        return [c.name for c in Country]

    def _resolve_keywords(self) -> List[str]:
        keywords = self._split_csv(getattr(settings, "KEYWORDS", None))
        if not keywords:
            logger.warning("⚠️ No KEYWORDS configured; nothing to search for.")
        return keywords

    @staticmethod
    def _country_value(country_name: str) -> str:
        """
        Convert a Country enum name (case-insensitive) to its value.
        Raises a clear error if the name is invalid.
        """
        try:
            return Country[country_name.upper()].value
        except KeyError as e:
            valid = ", ".join([c.name for c in Country])
            raise ValueError(f"Unknown country '{country_name}'. Valid: {valid}") from e

    # -------------------------
    # DOM helpers
    # -------------------------
    def _has_no_results(self) -> bool:
        return bool(self.driver.find_elements(By.CLASS_NAME, "jobs-search-no-results-banner"))

    def _has_expired(self) -> bool:
        return self.driver.find_elements(By.XPATH, '//*[text()="No longer accepting applications"]') > 0

    def _has_exhausted_limitation(self) -> bool:
        return len(self.driver.find_elements(By.XPATH, '//*[text()="You’ve reached today\'s Easy Apply limit. Great effort applying today. We limit daily submissions to help ensure each application gets the right attention. Save this job and continue applying tomorrow."]')) > 0
