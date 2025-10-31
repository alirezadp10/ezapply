import time
from loguru import logger
from selenium.webdriver.common.by import By
from bot.config import settings
from bot.helpers import country_value, has_no_results, has_expired, has_exhausted_limit
from bot.utils import wait_until_page_loaded

def process_country_keyword(bot, country: str, keyword: str, real_apply: bool = False) -> None:
    country_val = country_value(country)
    url = bot.finder.build_job_url(keyword, country_val)

    bot.driver.get(url)
    wait_until_page_loaded(bot.driver, url)

    if has_no_results(bot.driver):
        logger.info(f"ℹ️ No results for '{keyword}' in '{country}'. Skipping.")
        return

    jobs = _safe_get_easy_apply_jobs(bot)
    if not jobs:
        logger.info(f"ℹ️ No easy-apply jobs found for '{keyword}' in '{country}'.")
        return

    for job in jobs:
        if bot.db.is_applied_for_job(job["id"]):
            logger.info(f"ℹ️ Already applied to job #{job['id']}, skipping.")
            continue

        job_url = bot.finder.build_job_url(job_id=job["id"])
        try:
            bot.driver.get(job_url)
            time.sleep(settings.DELAY_TIME)
            if has_expired(bot.driver):
                continue
            if has_exhausted_limit(bot.driver):
                logger.error("❌ Daily limit reached. Stopping.")
                exit(1)

            wait_until_page_loaded(
                bot.driver,
                f'div[data-job-id="{job["id"]}"]',
                wait_for=(By.ID, "jobs-apply-button-id"),
            )
            if real_apply:
                bot.applicator.apply_to_job(job["id"])
            bot.db.save_job(
                title=job["title"],
                job_id=job["id"],
                status="applied",
                url=f"{url}&currentJobId={job['id']}",
            )
            logger.success(f"✅ Applied to job #{job['id']} '{job['title']}' in '{country}'")
        except Exception as e:
            logger.error(f"❌ Error applying to job #{job['id']} '{job['title']}': {e}")
            bot.db.save_job(
                title=job["title"],
                job_id=job["id"],
                status="failed",
                url=f"{url}&currentJobId={job['id']}",
                reason=str(e),
            )

def _safe_get_easy_apply_jobs(bot):
    try:
        jobs = bot.finder.get_easy_apply_jobs() or []
        return [{"id": j["id"], "title": j.get("title", "")} for j in jobs if "id" in j]
    except Exception as e:
        logger.error(f"❌ Failed to fetch Easy Apply jobs: {e}")
        return []
