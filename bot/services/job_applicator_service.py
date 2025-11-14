from __future__ import annotations

from typing import Any, Dict, Iterable, List

import numpy as np
from loguru import logger
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from bot.agents import FormAnswerAgent
from bot.enums import ElementsEnum, JobStatusEnum
from bot.exceptions import JobApplyError
from bot.helpers.dom_utils import click_if_exists, find_elements
from bot.helpers.form_utils import (
    extract_checkbox_groups,
    extract_fields,
    extract_radio_groups,
    extract_textareas,
    handle_fieldset,
    handle_generic_editable,
    handle_input,
    handle_select,
    handle_textarea,
    infer_type,
    wait_present_by_id,
)
from bot.models import Job
from bot.schemas import FormItemSchema
from bot.services import EmbeddingService
from bot.settings import settings


class JobApplicatorService:
    def __init__(self, driver, db, wait_seconds: int = 10):
        self.driver = driver
        self.db = db
        self.wait = WebDriverWait(driver, wait_seconds)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def run(self, job: Job, submit: bool) -> None:
        try:
            step_count = 0
            while True:
                step_count += 1
                if step_count > settings.MAX_STEPS_PER_APPLICATION:
                    raise JobApplyError(
                        f"Exceeded {settings.MAX_STEPS_PER_APPLICATION} steps; aborting to avoid an infinite loop."
                    )

                payload = self.parse_form_fields()

                if payload:
                    items = self._prepare_items_with_embeddings(payload)
                    self._hydrate_answers_from_history(items)
                    ai_answers = self._generate_ai_answers_for_unanswered(items)
                    self._merge_ai_answers(items, ai_answers)
                    fields = self.fill_fields(payload, items)
                    self._persist_filled_fields(fields, job.id)

                if self._has_error_icon():
                    self._close_and_discard()
                    self.db.job.update_status(pk=job.id, status=JobStatusEnum.FILL_OUT_FORM)
                    logger.error(f"❌ Couldn't fill out the form. {job.url}")
                    return

                if self._check_questions_have_been_finished():
                    if not submit:
                        self.db.job.update_status(pk=job.id, status=JobStatusEnum.READY_FOR_APPLY)
                        logger.error("✅ Job is ready for apply.")
                        return

                    self.db.job.update_status(pk=job.id, status=JobStatusEnum.APPLIED)
                    logger.error("✅ Job has been submitted.")
                    return

                if self._next_step():
                    continue
        except Exception as e:
            logger.error(f"❌ {str(e)}")
            return

    # -------------------------------------------------------------------------
    # Navigation helpers
    # -------------------------------------------------------------------------
    def _next_step(self) -> bool:
        """
        Attempts to go to the next step (or review). Returns True if we clicked something.
        """
        for sel in [ElementsEnum.NEXT_STEP_BUTTON, ElementsEnum.REVIEW_BUTTON]:
            if click_if_exists(self.driver, By.CSS_SELECTOR, sel):
                return True
        return False

    def _check_questions_have_been_finished(self) -> bool:
        return bool(self.driver.find_elements(By.CSS_SELECTOR, ElementsEnum.SUBMIT_BUTTON))

    def _has_error_icon(self) -> bool:
        return bool(self.driver.find_elements(By.CSS_SELECTOR, ElementsEnum.ERROR_ICON))

    def _close_and_discard(self) -> None:
        click_if_exists(self.driver, By.CSS_SELECTOR, ElementsEnum.DISMISS_BUTTON)
        click_if_exists(self.driver, By.CSS_SELECTOR, ElementsEnum.DISCARD_BUTTON)

    # -------------------------------------------------------------------------
    # Data/DB helpers
    # -------------------------------------------------------------------------
    def _persist_filled_fields(self, fields: List[FormItemSchema], job_id: int) -> None:
        """
        Persists field label/value/type with *fresh* embeddings of the label.
        """
        for field in fields:
            embeddings = EmbeddingService.get_embedding(field.label)
            saved_field = self.db.field.insert(
                label=field.label,
                value=field.answer,
                type=field.type,
                embeddings=embeddings,
            )
            self.db.field_job.insert(field_id=saved_field.id, job_id=job_id)

    # -------------------------------------------------------------------------
    # Answer pipeline
    # -------------------------------------------------------------------------
    def _prepare_items_with_embeddings(self, payload: List[Dict[str, str]]) -> List[FormItemSchema]:
        """
        Takes raw parsed payload -> FormItemSchema list, computes and attaches embeddings (float32 bytes).
        """
        items = [FormItemSchema.from_payload_entry(p) for p in payload]
        for item in items:
            emb = EmbeddingService.get_embedding(item.label)
            item.embeddings = np.asarray(emb, dtype=np.float32).tobytes()
        return items

    def _hydrate_answers_from_history(self, items: List[FormItemSchema]) -> None:
        """
        Fills answers for items whose labels closely match previously stored fields,
        using cosine similarity on embeddings. Operates in-place.
        """
        historical = self.db.field.get_all()
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

    # -------------------------------------------------------------------------
    # Parse form pipeline
    # -------------------------------------------------------------------------
    def parse_form_fields(self) -> List[Dict[str, str]]:
        """Parse visible and enabled input, select, textarea, checkbox, and radio fields from the modal form."""
        try:
            modal = find_elements(
                driver=self.driver,
                by=By.CSS_SELECTOR,
                selector=ElementsEnum.MODAL,
                retries=5,
                index=0,
            )
        except NoSuchElementException:
            logger.error("❌ could not find modal element")
            return []

        form = next(iter(modal.find_elements(By.TAG_NAME, ElementsEnum.FORM)), None)
        if not form:
            return []

        fields = (
            extract_fields(
                form,
                ElementsEnum.INPUT_NOT_RADIO,
                include_fn=lambda el: el.is_displayed() and el.is_enabled() and not el.get_attribute("value"),
            )
            + extract_fields(
                form,
                ElementsEnum.SELECT,
                include_fn=lambda el: (
                    el.is_displayed()
                    and el.is_enabled()
                    and ((el.get_attribute("value") or "").strip() in ("", "Select an option"))
                ),
                include_options=True,
            )
            + extract_textareas(form)
            + extract_checkbox_groups(form)
            + extract_radio_groups(form)
        )

        return fields

    # -------------------------------------------------------------------------
    # Filling fields
    # -------------------------------------------------------------------------
    def fill_fields(
        self,
        fields: Iterable[Dict[str, Any]],
        answers: Iterable[FormItemSchema],
    ) -> List[FormItemSchema]:
        """
        Fill collection of form fields using (label -> answer) pairs.

        Returns a list of FormItemSchema rows describing what was attempted.
        """
        result: List[FormItemSchema] = []
        answer_map = {str(a.label): a.answer for a in answers}

        for item in fields:
            field_id = item["id"]
            label = item["label"]

            el = wait_present_by_id(self.wait, field_id)

            inferred_type = infer_type(el)
            answer = answer_map.get(label)

            result.append(FormItemSchema(label=label, answer=answer, type=inferred_type))

            # Skip if no provided answer, but still report in result
            if answer in (None, ""):
                continue

            tag = el.tag_name.lower()

            if tag == "input":
                handle_input(self.driver, el, answer)
            elif tag == "select":
                handle_select(self.driver, el, answer)
            elif tag == "textarea":
                handle_textarea(self.driver, el, answer)
            elif tag == "fieldset":
                handle_fieldset(self.driver, self.wait, el, answer)
            else:
                handle_generic_editable(self.driver, el, answer)

        return result
