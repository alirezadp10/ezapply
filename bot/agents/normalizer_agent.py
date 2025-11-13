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
    def ask(job_title: str, job_description: str) -> NormalizerOutputSchema:
        prompt = f"""
        JOB TITLE:
        {job_title}

        JOB DESCRIPTION:
        {job_description}

        CANDIDATE PROFILE:
        {settings.USER_INFORMATION}

        Extract and normalize both job and candidate.
        """

        return (
            Agent(
                model=settings.OPENAI_MODEL_NAME,
                system_prompt=NORMALIZER_SYSTEM_PROMPT,
                output_type=NormalizerOutputSchema,
            )
            .run_sync(prompt)
            .output
        )
