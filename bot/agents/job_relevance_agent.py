import time

from loguru import logger
from pydantic_ai import Agent

from bot.settings import settings

IS_RELEVANT_SYSTEM_PROMPT = """
You are a Job Relevance Classifier.

Your ONLY task:
Given a job title and a list of target keywords,
you must answer ONLY "yes" or "no".

Rules:
- Do NOT explain.
- Do NOT add anything else.
- Respond strictly with: yes  OR  no.
"""


class JobRelevanceAgent:
    @staticmethod
    def ask(title: str) -> bool:
        prompt = f"""
        JOB TITLE:
        {title}

        TARGET KEYWORDS:
        {settings.KEYWORDS}

        Is this job relevant?
        """

        agent = Agent(
            name="job_relevance_classifier",
            model=settings.OPENAI_MODEL_NAME,
            system_prompt=IS_RELEVANT_SYSTEM_PROMPT,
            output_type=str,
        )

        for attempt in range(1, settings.AI_MAX_RETRIES + 1):
            try:
                result = (
                    agent.run_sync(prompt)
                    .output.strip()
                    .lower()
                )
                return result == "yes"

            except Exception as e:
                logger.warning(
                    f"⚠️ JobRelevanceAgent error on attempt "
                    f"{attempt}/{settings.AI_MAX_RETRIES}: {e}"
                )

                if attempt == settings.AI_MAX_RETRIES:
                    logger.error("❌ JobRelevanceAgent failed after all retries")
                    raise

                sleep_time = settings.AI_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info(f"⏳ Retrying in {sleep_time:.1f}s…")
                time.sleep(sleep_time)
