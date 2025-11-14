from typing import Optional

from bot.enums import WorkTypesEnum
from bot.settings import settings


def build_job_url(
        keyword: Optional[str] = None,
        country_id: Optional[str] = None,
        job_id: Optional[str] = None,
) -> str:
    base = settings.LINKEDIN_BASE_URL

    if job_id:
        return f"{base}/jobs/search?currentJobId={job_id}"

    params = {}
    if keyword:
        params["keywords"] = f'"{keyword.strip()}"'
    if country_id:
        params["geoId"] = country_id

    params["f_TPR"] = f"r{settings.JOB_SEARCH_TIME_WINDOW}"
    params["f_WT"] = WorkTypesEnum(settings.WORK_TYPE)

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}/jobs/search?{query}"
