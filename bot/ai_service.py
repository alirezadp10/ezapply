import json, re, requests
from loguru import logger
from bot.config import settings

class AIService:
    @staticmethod
    def ask_form_answers(payload):
        labels = [{"label": item["label"], "answer": ""} for item in payload]
        body = {
            "model": settings.DEEPINFRA_MODEL_NAME,
            "messages": [{
                "role": "system",
                "content": (
                    f"Based on this information: ({settings.USER_INFORMATION}) "
                    f"fill out this object: {json.dumps(labels)}. "
                    "Return only the list, no explanations."
                )
            }]
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        }

        try:
            res = requests.post(settings.DEEPINFRA_API_URL, headers=headers, json=body, timeout=60).json()
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            return AIService._extract_json_array(content)
        except Exception as e:
            logger.warning(f"⚠️ AI request failed: {e}")
            return []

    @staticmethod
    def is_relevant_job(title: str, keyword: str) -> bool:
        body = {
            "model": settings.DEEPINFRA_MODEL_NAME,
            "messages": [{
                "role": "system",
                "content": f"Is the job '{title}' relevant to a {keyword} position? Answer yes or no."
            }]
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        }

        try:
            res = requests.post(settings.DEEPINFRA_API_URL, headers=headers, json=body, timeout=60).json()
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
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
