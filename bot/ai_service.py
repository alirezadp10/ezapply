import json
import re
from typing import Any, Dict, List, Optional

import requests
from loguru import logger
from bot.config import settings


class AIService:
    """Service wrapper around DeepInfra endpoints with consistent error handling."""

    _TIMEOUT_DEFAULT = 60
    _SESSION: Optional[requests.Session] = None

    # ---------- Internal utilities ----------

    @classmethod
    def _session(cls) -> requests.Session:
        if cls._SESSION is None:
            cls._SESSION = requests.Session()
            cls._SESSION.headers.update({"Content-Type": "application/json"})
        return cls._SESSION

    @staticmethod
    def _auth_headers() -> Dict[str, str]:
        return {"Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}"}

    @classmethod
    def _post_json(
        cls,
        url: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """POST JSON and return parsed JSON (or empty dict on error)."""
        try:
            resp = cls._session().post(
                url,
                headers=cls._auth_headers(),
                json=payload,
                timeout=timeout or cls._TIMEOUT_DEFAULT,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"⚠️ POST {url} failed: {e}")
            return {}

    @staticmethod
    def _extract_json_array(text: str) -> List[Any]:
        """
        Attempt to extract the first JSON array from `text`.
        Falls back to removing newlines if initial parse fails.
        """
        match = re.search(r"\[.*]", text, re.DOTALL)
        if not match:
            return []
        candidate = match.group(0)

        try:
            return json.loads(candidate)
        except Exception:
            # remove line breaks and retry
            cleaned = re.sub(r"[\r\n]", "", candidate)
            try:
                return json.loads(cleaned)
            except Exception:
                return []

    # ---------- Public API ----------

    @staticmethod
    def ask_form_answers(labels: List[Dict[str, Any]]) -> List[Any]:
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

        res = AIService._post_json(settings.DEEPINFRA_API_URL, body)
        content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
        return AIService._extract_json_array(content)

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

        res = AIService._post_json(settings.DEEPINFRA_API_URL, body)
        content = res.get("choices", [{}])[0].get("message", {}).get("content", "")

        return (content or "").strip().lower() == "yes"

    @staticmethod
    def get_embedding(text: str) -> List[float]:
        try:
            resp = AIService._session().post(
                settings.DEEPINFRA_EMBEDDING_API_URL,
                headers={
                    **AIService._auth_headers(),
                    "Content-Type": "application/json",
                },
                json={"inputs": [text]},
                timeout=AIService._TIMEOUT_DEFAULT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embeddings", [])
        except Exception as e:
            logger.warning(f"⚠️ Embedding request failed: {e}")
            # Preserve original behavior of raising on HTTP error was present,
            # but we prefer to degrade gracefully here returning an empty list.
            return []
