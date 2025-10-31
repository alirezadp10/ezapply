from loguru import logger

from bot.enums import ModesEnum
from bot.helpers import parse_job_ids_from_string, resolve_countries, resolve_keywords
from bot.job_runner import process_country_keyword
from bot.test_runner import run_test_jobs


def run_mode(mode: str, bot, job_ids: str = "") -> None:
    if mode == ModesEnum.TEST:
        ids = parse_job_ids_from_string(job_ids)
        if not ids:
            logger.warning("⚠️ No job IDs provided. Use --ids or TEST_WITH env var.")
            return
        run_test_jobs(bot, ids)

    elif mode == ModesEnum.EXPLORE:
        countries = resolve_countries()
        keywords = resolve_keywords()
        for country in countries:
            for keyword in keywords:
                process_country_keyword(bot, country, keyword)

    elif mode == ModesEnum.FAKE:
        logger.info("🤖 Running in fake apply mode (no real submissions).")
        # TODO: simulate form filling only

    elif mode == ModesEnum.REAL:
        logger.info("🧑‍💼 Running in real apply mode.")
        countries = resolve_countries()
        keywords = resolve_keywords()
        for country in countries:
            for keyword in keywords:
                process_country_keyword(bot, country, keyword, real_apply=True)

    else:
        raise ValueError(f"Unknown mode '{mode}'")
