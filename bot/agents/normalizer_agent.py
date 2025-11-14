import time

from loguru import logger
from pydantic_ai import Agent

from bot.schemas import NormalizerOutputSchema
from bot.settings import settings

NORMALIZER_SYSTEM_PROMPT = """
You are a Normalization Agent.

Your ONLY job:
Turn messy job postings & messy candidate profiles into a clean,
standardized JSON format based on the output schema.

Rules:
- DO NOT evaluate or score.
- DO NOT say whether the candidate fits the job.
- Only extract, clean, standardize, normalize.
- Use lowercase for technologies and tags.
- Extract seniority (junior/mid/senior/lead) when possible.
- Extract technologies even if they appear in sentences.
- Always return STRICT JSON matching the output schema.

Your output MUST follow this structure:

{
  "job_normalized": {...},
  "candidate_normalized": {...}
}
"""


class NormalizerAgent:
    @staticmethod
    def ask(job_title: str, job_description: str):
        prompt = f"""
        JOB TITLE:
        {job_title}

        JOB DESCRIPTION:
        {job_description}

        CANDIDATE PROFILE:
        {settings.USER_INFORMATION}

        Extract and normalize both job and candidate.
        """

        agent = Agent(
            name="normalizer",
            model=settings.OPENAI_MODEL_NAME,
            system_prompt=NORMALIZER_SYSTEM_PROMPT,
            output_type=NormalizerOutputSchema,
        )

        # Retry loop
        for attempt in range(1, settings.AI_MAX_RETRIES + 1):
            try:
                return agent.run_sync(prompt).output

            except Exception as e:
                logger.warning(f"⚠️ NormalizerAgent error on attempt {attempt}/{settings.AI_MAX_RETRIES}: {e}")

                # If this was the last retry -> re-raise
                if attempt == settings.AI_MAX_RETRIES:
                    logger.error("❌ NormalizerAgent failed after all retries")
                    raise

                # Otherwise: exponential backoff
                sleep_time = settings.AI_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info(f"⏳ Retrying in {sleep_time:.1f}s…")
                time.sleep(sleep_time)
