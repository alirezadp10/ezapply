import time
from loguru import logger
from pydantic_ai import Agent
from bot.settings import settings

ASK_FORM_SYSTEM_PROMPT = """
You are a Form-Filling AI.

Your job:
- Given the candidate information and a list of label objects,
  fill in the answers.
- If the candidate information does not contain an answer,
  you MUST make up a reasonable value.
- For numbers and salaries, return only integers.
- You MUST return ONLY a JSON list. No explanations.
"""


class FormAnswerAgent:
    MAX_RETRIES = 4
    BACKOFF_BASE = 0.5  # seconds

    @staticmethod
    def ask(labels):
        prompt = f"""
        CANDIDATE INFORMATION:
        {settings.USER_INFORMATION}

        FORM LABELS TO FILL:
        {labels}

        Return ONLY the list.
        """

        agent = Agent(
            name="form_answer_agent",
            model=settings.OPENAI_MODEL_NAME,
            system_prompt=ASK_FORM_SYSTEM_PROMPT,
            output_type=list,
        )

        for attempt in range(1, FormAnswerAgent.MAX_RETRIES + 1):
            try:
                result = agent.run_sync(prompt).output
                return result

            except Exception as e:
                logger.warning(
                    f"⚠️ FormAnswerAgent error on attempt "
                    f"{attempt}/{FormAnswerAgent.MAX_RETRIES}: {e}"
                )

                if attempt == FormAnswerAgent.MAX_RETRIES:
                    logger.error("❌ FormAnswerAgent failed after all retries")
                    raise

                sleep_time = FormAnswerAgent.BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info(f"⏳ Retrying in {sleep_time:.1f}s…")
                time.sleep(sleep_time)
