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
    @staticmethod
    def ask(labels):
        prompt = f"""
        CANDIDATE INFORMATION:
        {settings.USER_INFORMATION}

        FORM LABELS TO FILL:
        {labels}

        Return ONLY the list.
        """

        return (
            Agent(
                model=settings.OPENAI_MODEL_NAME,
                system_prompt=ASK_FORM_SYSTEM_PROMPT,
                output_type=list,
            )
            .agent.run_sync(prompt)
            .output
        )
