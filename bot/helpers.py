import os
from typing import Optional, List
from loguru import logger
from selenium.webdriver.common.by import By
from bot.config import settings
from bot.enums import Country

def read_test_job_ids() -> List[str]:
    raw = os.getenv("TEST_WITH", "").strip()
    return [t.strip() for t in raw.split(",") if t.strip()]

def split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]

def resolve_countries() -> List[str]:
    configured = split_csv(getattr(settings, "COUNTRIES", None))
    return [c.upper() for c in configured] if configured else [c.name for c in Country]

def resolve_keywords() -> List[str]:
    keywords = split_csv(getattr(settings, "KEYWORDS", None))
    if not keywords:
        logger.warning("⚠️ No KEYWORDS configured; nothing to search for.")
    return keywords

def country_value(country_name: str) -> str:
    try:
        return Country[country_name.upper()].value
    except KeyError as e:
        valid = ", ".join([c.name for c in Country])
        raise ValueError(f"Unknown country '{country_name}'. Valid: {valid}") from e

# --- DOM helpers ---
def has_no_results(driver) -> bool:
    return bool(driver.find_elements(By.CLASS_NAME, "jobs-search-no-results-banner"))

def has_expired(driver) -> bool:
    return bool(driver.find_elements(By.XPATH, '//*[text()="No longer accepting applications"]'))

def has_exhausted_limit(driver) -> bool:
    xpath = ("//*[text()=\"You’ve reached today's Easy Apply limit. "
             "Great effort applying today. We limit daily submissions "
             "to help ensure each application gets the right attention.\"]")
    return bool(driver.find_elements(By.XPATH, xpath))

def parse_job_ids_from_string(raw: str) -> List[str]:
    raw = raw or os.getenv("TEST_WITH", "")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]
