import json
import re
import requests
from loguru import logger
from bot.config import settings


class AIService:
    @staticmethod
    def ask_form_answers(labels):
        body = {
            "model": settings.DEEPINFRA_MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Based on this information: ({settings.USER_INFORMATION}) "
                        f"fill out this object: {json.dumps(labels)}. "
                        "If you cannot find the answer to a question based on the information, make it up by yourself. "
                        "For numbers and salaries, please mention only the integer value. "
                        "Return only the list, no explanations."
                    ),
                }
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        }

        try:
            res = requests.post(
                settings.DEEPINFRA_API_URL, headers=headers, json=body, timeout=60
            ).json()
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            return AIService._extract_json_array(content)
        except Exception as e:
            logger.warning(f"⚠️ AI request failed: {e}")
            return []

    @staticmethod
    def is_relevant_job(title: str) -> bool:
        body = {
            "model": settings.DEEPINFRA_MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": f"Is the job '{title}' relevant to any positions like {settings.KEYWORDS}? Just answer yes or no without any extra.",
                }
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        }

        try:
            res = requests.post(
                settings.DEEPINFRA_API_URL, headers=headers, json=body, timeout=60
            ).json()
            content = (
                res.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
                .lower()
            )
            return content == "yes"
        except Exception as e:
            logger.warning(f"⚠️ AI relevance check failed: {e}")
            return False

    @staticmethod
    def _extract_json_array(text: str):
        match = re.search(r"\[.*]", text, re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except Exception:
            cleaned = re.sub(r"[\r\n]", "", match.group(0))
            try:
                return json.loads(cleaned)
            except Exception:
                return []

    @staticmethod
    def get_embedding(text: str) -> list:
        resp = requests.post(
            settings.DEEPINFRA_EMBEDDING_API_URL,
            headers={
                "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": [text],
            },
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]
