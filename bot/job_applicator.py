from __future__ import annotations

from typing import List, Dict

import numpy as np
from loguru import logger
from selenium.webdriver.common.by import By

from bot.ai_service import AIService
from bot.config import settings
from bot.embedding_manager import EmbeddingManager
from bot.enums import ElementsEnum
from bot.exceptions import JobApplyError, FormFillError, ApplyButtonNotFound
from bot.form_parser import FormParser
from bot.form_filler import FormFiller
from bot.dto import FormItemDTO
from bot.utils import wait_until_page_loaded


class JobApplicator:
    """
    Orchestrates a multi_step job application flow:
    - Clicks 'Apply'
    - Iteratively parses current step, finds/creates answers
    - Fills fields and persists them
    - Advances steps and submits when ready
    """

    def __init__(self, driver, db):
        self.driver = driver
        self.db = db
        self.parser = FormParser(driver)
        self.embedding_manager = EmbeddingManager()
        self.filler = FormFiller(driver)

    # Public API ---------------------------------------------------------------

    def apply_to_job(self, job_id: str):
        """
        Returns True if submitted successfully, otherwise raises JobApplyError.
        """
        self._click_apply_or_fail()

        step_count = 0
        while True:
            step_count += 1
            if step_count > settings.MAX_STEPS_PER_APPLICATION:
                raise JobApplyError(
                    f"Exceeded {settings.MAX_STEPS_PER_APPLICATION} steps; aborting to avoid an infinite loop."
                )

            payload = self.parser.parse_form_fields()

            if payload:
                items = self._prepare_items_with_embeddings(payload)
                self._hydrate_answers_from_history(items)
                ai_answers = self._generate_ai_answers_for_unanswered(items)
                # Merge AI answers into items
                self._merge_ai_answers(items, ai_answers)

                # Fill and persist
                fields = self.filler.fill_fields(
                    payload, items
                )  # expects items as answers with labels
                self._persist_filled_fields(fields, job_id)

            # Early surface of form-level errors
            if self._has_error_icon():
                self._close_and_discard()
                raise FormFillError("Couldn't fill out the form.")

            # Submit if ready
            if self._submit_if_ready(job_id):
                return True

            # Otherwise continue/review
            if self._next_step():
                continue

            # If neither submit nor next-step is available and no payload, we may be stuck.
            # Fail fast with a helpful message.
            if not payload:
                raise JobApplyError(
                    "No form payload and cannot advance; the flow may be in an unexpected state."
                )

    # Click & navigation helpers ----------------------------------------------

    def _click_apply_or_fail(self) -> None:
        try:
            wait_until_page_loaded(self.driver, ElementsEnum.APPLY_BTN_ID)
            self.driver.find_element(By.ID, ElementsEnum.APPLY_BTN_ID).click()
        except Exception as exc:
            raise ApplyButtonNotFound(
                "Couldn't find or click the apply button."
            ) from exc

    def _next_step(self) -> bool:
        """
        Attempts to go to the next step (or review). Returns True if we clicked something.
        """
        return self._click_if_exists(
            ElementsEnum.SEL_NEXT_STEP
        ) or self._click_if_exists(ElementsEnum.SEL_REVIEW)

    def _submit_if_ready(self, job_id: str) -> bool:
        if self._click_if_exists(ElementsEnum.SEL_SUBMIT):
            logger.info(f"✅ Job {job_id} submitted.")
            self._click_if_exists(ElementsEnum.SEL_DISMISS)  # best-effort
            return True
        return False

    def _click_if_exists(self, selector: str, retries: int = 1) -> bool:
        """
        Best-effort click by CSS selector. Optional small retry window.
        """
        for attempt in range(retries + 1):
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                el.click()
                wait_until_page_loaded(self.driver, selector)
                return True
            except Exception:
                if attempt == retries:
                    return False
        return False

    def _has_error_icon(self) -> bool:
        return bool(
            self.driver.find_elements(By.CSS_SELECTOR, ElementsEnum.SEL_ERROR_ICON)
        )

    def _close_and_discard(self) -> None:
        self._click_if_exists(ElementsEnum.SEL_DISMISS)
        self._click_if_exists(ElementsEnum.SEL_DISCARD)

    # Data/DB helpers ----------------------------------------------------------

    def _persist_filled_fields(self, fields: List[FormItemDTO], job_id: str) -> None:
        """
        Persists field label/value/type with *fresh* embeddings of the label.
        """
        for field in fields:
            embeddings = AIService.get_embedding(field.label)
            self.db.save_field(
                label=field.label,
                value=field.answer,
                type=field.type,
                embeddings=embeddings,
                job_id=job_id,
            )

    # Answer pipeline ----------------------------------------------------------

    def _prepare_items_with_embeddings(
        self, payload: List[Dict[str, str]]
    ) -> List[FormItemDTO]:
        """
        Takes raw parsed payload -> FormItemDTO list, computes and attaches embeddings (float32 bytes).
        """
        items = [FormItemDTO.from_payload_entry(p) for p in payload]
        for item in items:
            emb = AIService.get_embedding(item.label)
            item.embeddings = np.asarray(emb, dtype=np.float32).tobytes()
        return items

    def _hydrate_answers_from_history(self, items: List["FormItemDTO"]) -> None:
        """
        Fills answers for items whose labels closely match previously stored fields,
        using cosine similarity on embeddings. Operates in-place.
        """

        # Load historical fields once
        historical = (
            self.db.get_all_fields()
        )  # expects objects with .embedding, .label, .value
        if not historical or not items:
            return

        self.embedding_manager.fill_out_items(items, historical)

    def _generate_ai_answers_for_unanswered(
        self, items: List[FormItemDTO]
    ) -> List[Dict[str, str]]:
        """
        Calls AI service for only unanswered items. Returns AI-produced answers
        as a list of dicts with keys: label, answer, embeddings (optional).
        """
        unanswered = [{"label": i.label, "answer": ""} for i in items if not i.answer]
        if not unanswered:
            return []
        return AIService.ask_form_answers(unanswered)

    def _merge_ai_answers(
        self, items: List[FormItemDTO], ai_answers: List[Dict[str, str]]
    ) -> None:
        """
        Merge AI answers into items in-place by label.
        """
        if not ai_answers:
            return
        lookup = {a["label"]: a.get("answer", "") for a in ai_answers}
        for item in items:
            if not item.answer and item.label in lookup:
                item.answer = lookup[item.label]
