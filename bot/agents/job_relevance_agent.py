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

        result = (
            Agent(
                model=settings.OPENAI_MODEL_NAME,
                system_prompt=IS_RELEVANT_SYSTEM_PROMPT,
                output_type=str,
            )
            .run_sync(prompt)
            .output.strip()
            .lower()
        )

        return result == "yes"
