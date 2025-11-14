from __future__ import annotations

from typing import Dict, List

import numpy as np
from loguru import logger
from selenium.webdriver.common.by import By

from bot.agents import FormAnswerAgent
from bot.enums import ElementsEnum, JobStatusEnum
from bot.exceptions import JobApplyError
from bot.helpers.helpers import click_if_exists
from bot.schemas import FormItemSchema
from bot.services import EmbeddingService, FormFillerService, FormParserService
from bot.settings import settings


class JobApplicatorService:
    def __init__(self, driver, db):
        self.driver = driver
        self.db = db
        self.parser = FormParserService(driver)
        self.filler = FormFillerService(driver)

    def apply_to_job(self, job_id: int):
        try:
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
                    self._merge_ai_answers(items, ai_answers)
                    fields = self.filler.fill_fields(payload, items)
                    self._persist_filled_fields(fields, job_id)

                if self._has_error_icon():
                    self._close_and_discard()
                    self.db.update_job_status(pk=job_id, status=JobStatusEnum.FILL_OUT_FORM)
                    logger.error("❌ Couldn't fill out the form.")
                    return

                if self._check_questions_have_been_finished():
                    self.db.update_job_status(pk=job_id, status=JobStatusEnum.READY_FOR_APPLY)
                    logger.error("✅ Job is ready for apply.")
                    return

                if self._next_step():
                    continue
        except Exception as e:
            logger.error(f"❌ {str(e)}")
            return

    def _next_step(self) -> bool:
        """
        Attempts to go to the next step (or review). Returns True if we clicked something.
        """
        for sel in [ElementsEnum.NEXT_STEP_BUTTON, ElementsEnum.REVIEW_BUTTON]:
            if click_if_exists(self.driver, By.CSS_SELECTOR, sel):
                return True
        return False

    def _check_questions_have_been_finished(self) -> bool:
        if self.driver.find_elements(By.CSS_SELECTOR, ElementsEnum.SUBMIT_BUTTON):
            return True
        return False

    def _has_error_icon(self) -> bool:
        return bool(self.driver.find_elements(By.CSS_SELECTOR, ElementsEnum.ERROR_ICON))

    def _close_and_discard(self) -> None:
        click_if_exists(self.driver, By.CSS_SELECTOR, ElementsEnum.DISMISS_BUTTON)
        click_if_exists(self.driver, By.CSS_SELECTOR, ElementsEnum.DISCARD_BUTTON)

    # Data/DB helpers ----------------------------------------------------------

    def _persist_filled_fields(self, fields: List[FormItemSchema], job_id: int) -> None:
        """
        Persists field label/value/type with *fresh* embeddings of the label.
        """
        for field in fields:
            embeddings = EmbeddingService.get_embedding(field.label)
            saved_field = self.db.save_field(
                label=field.label,
                value=field.answer,
                type=field.type,
                embeddings=embeddings,
            )
            self.db.save_field_job(field_id=saved_field.id, job_id=job_id)

    # Answer pipeline ----------------------------------------------------------

    def _prepare_items_with_embeddings(self, payload: List[Dict[str, str]]) -> List[FormItemSchema]:
        """
        Takes raw parsed payload -> FormItemSchema list, computes and attaches embeddings (float32 bytes).
        """
        items = [FormItemSchema.from_payload_entry(p) for p in payload]
        for item in items:
            emb = EmbeddingService.get_embedding(item.label)
            item.embeddings = np.asarray(emb, dtype=np.float32).tobytes()
        return items

    def _hydrate_answers_from_history(self, items: List["FormItemSchema"]) -> None:
        """
        Fills answers for items whose labels closely match previously stored fields,
        using cosine similarity on embeddings. Operates in-place.
        """

        # Load historical fields once
        historical = self.db.get_all_fields()  # expects objects with .embedding, .label,
        if not historical or not items:
            return

        EmbeddingService.fill_out_items(items, historical)

    def _generate_ai_answers_for_unanswered(self, items: List[FormItemSchema]) -> List[Dict[str, str]]:
        """
        Calls AI service for only unanswered items. Returns AI-produced answers
        as a list of dicts with keys: label, answer, embeddings (optional).
        """
        unanswered = [{"label": i.label, "answer": ""} for i in items if not i.answer]
        if not unanswered:
            return []
        return FormAnswerAgent.ask(unanswered)

    def _merge_ai_answers(self, items: List[FormItemSchema], ai_answers: List[Dict[str, str]]) -> None:
        """
        Merge AI answers into items in-place by label.
        """
        if not ai_answers:
            return
        lookup = {a["label"]: a.get("answer", "") for a in ai_answers}
        for item in items:
            if not item.answer and item.label in lookup:
                item.answer = lookup[item.label]
