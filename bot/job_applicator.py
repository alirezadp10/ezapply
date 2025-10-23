from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Iterable, Tuple

import numpy as np
from loguru import logger
from selenium.webdriver.common.by import By

from bot.ai_service import AIService
from bot.form_parser import FormParser
from bot.form_filler import FormFiller
from bot.utils import wait_until_page_loaded


# ---------------------------
# Constants & configuration
# ---------------------------

APPLY_BTN_ID = "jobs-apply-button-id"

SEL_NEXT_STEP = '[aria-label="Continue to next step"]'
SEL_REVIEW     = '[aria-label="Review your application"]'
SEL_SUBMIT     = '[aria-label="Submit application"]'
SEL_DISMISS    = '[aria-label="Dismiss"]'
SEL_DISCARD    = '[data-control-name="discard_application_confirm_btn"]'
SEL_ERROR_ICON = '[type="error-pebble-icon"]'

# Similarity must be in [0, 1]. 0.95 was in original code; keep as default but make it tunable.
SIMILARITY_THRESHOLD = 0.95

# Defensive programming: cap the number of steps to avoid infinite loops due to site quirks
MAX_STEPS_PER_APPLICATION = 30

# ---------------------------
# Exceptions
# ---------------------------

class JobApplyError(RuntimeError):
    """Base exception for job application flow errors."""

class ApplyButtonNotFound(JobApplyError):
    """Raised when the initial apply button cannot be found/clicked."""

class FormFillError(JobApplyError):
    """Raised when we detect an error pebble during form filling."""


# ---------------------------
# Data structures
# ---------------------------

@dataclass
class FormItem:
    label: str
    answer: str = ""
    embeddings: bytes = b""  # float32 bytes

    @staticmethod
    def from_payload_entry(entry: Dict[str, str]) -> "FormItem":
        return FormItem(label=entry["label"])


# ---------------------------
# Main service
# ---------------------------

class JobApplicator:
    """
    Orchestrates a multi-step job application flow:
    - Clicks 'Apply'
    - Iteratively parses current step, finds/creates answers
    - Fills fields and persists them
    - Advances steps and submits when ready
    """

    def __init__(self, driver, db):
        self.driver = driver
        self.db = db
        self.parser = FormParser(driver)
        self.filler = FormFiller(driver)

    # Public API ---------------------------------------------------------------

    def apply_to_job(self, job_id: int) -> bool:
        """
        Returns True if submitted successfully, otherwise raises JobApplyError.
        """
        self._click_apply_or_fail()

        step_count = 0
        while True:
            step_count += 1
            if step_count > MAX_STEPS_PER_APPLICATION:
                raise JobApplyError(f"Exceeded {MAX_STEPS_PER_APPLICATION} steps; aborting to avoid an infinite loop.")

            payload = self.parser.parse_form_fields()

            if payload:
                items = self._prepare_items_with_embeddings(payload)
                self._hydrate_answers_from_history(items, threshold=SIMILARITY_THRESHOLD)
                ai_answers = self._generate_ai_answers_for_unanswered(items)
                # Merge AI answers into items
                self._merge_ai_answers(items, ai_answers)

                # Fill and persist
                fields = self.filler.fill_fields(payload, items)  # expects items as answers with labels
                self._persist_filled_fields(fields, job_id)

            # Early surface of form-level errors
            if self._has_error_icon():
                self._close_and_discard()
                raise FormFillError("Encountered an error while filling the form (error icon present).")

            # Submit if ready
            if self._submit_if_ready(job_id):
                return True

            # Otherwise continue/review
            if self._next_step():
                continue

            # If neither submit nor next-step is available and no payload, we may be stuck.
            # Fail fast with a helpful message.
            if not payload:
                raise JobApplyError("No form payload and cannot advance; the flow may be in an unexpected state.")

    # Click & navigation helpers ----------------------------------------------

    def _click_apply_or_fail(self) -> None:
        try:
            self.driver.find_element(By.ID, APPLY_BTN_ID).click()
            wait_until_page_loaded(self.driver, APPLY_BTN_ID)
        except Exception as exc:
            raise ApplyButtonNotFound("Couldn't find or click the apply button.") from exc

    def _next_step(self) -> bool:
        """
        Attempts to go to the next step (or review). Returns True if we clicked something.
        """
        return self._click_if_exists(SEL_NEXT_STEP) or self._click_if_exists(SEL_REVIEW)

    def _submit_if_ready(self, job_id: int) -> bool:
        if self._click_if_exists(SEL_SUBMIT):
            logger.info(f"✅ Job {job_id} submitted.")
            self._click_if_exists(SEL_DISMISS)  # best-effort
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
        return bool(self.driver.find_elements(By.CSS_SELECTOR, SEL_ERROR_ICON))

    def _close_and_discard(self) -> None:
        self._click_if_exists(SEL_DISMISS)
        self._click_if_exists(SEL_DISCARD)

    # Data/DB helpers ----------------------------------------------------------

    def _persist_filled_fields(self, fields: List[Dict], job_id: int) -> None:
        """
        Persists field label/value/type with *fresh* embeddings of the label.
        """
        for field in fields:
            embeddings = AIService.get_embedding(field["label"])
            self.db.save_field(
                label=field["label"],
                value=field["value"],
                type=field["type"],
                embeddings=embeddings,
                job_id=job_id,
            )

    # Answer pipeline ----------------------------------------------------------

    def _prepare_items_with_embeddings(self, payload: List[Dict[str, str]]) -> List[FormItem]:
        """
        Takes raw parsed payload -> FormItem list, computes and attaches embeddings (float32 bytes).
        """
        items = [FormItem.from_payload_entry(p) for p in payload]
        for item in items:
            emb = AIService.get_embedding(item.label)
            item.embeddings = np.asarray(emb, dtype=np.float32).tobytes()
        return items

    def _hydrate_answers_from_history(self, items: List[FormItem], threshold: float) -> None:
        """
        Fills answers for items whose labels closely match previously stored fields,
        using cosine similarity on embeddings. Operates in-place.
        """
        # Load historical fields once
        historical = self.db.get_all_fields()  # expects objects with .embedding, .label, .value
        if not historical or not items:
            return

        # Build matrices: query (n x d) and historical (m x d)
        q_mat = _stack_embeddings([i.embeddings for i in items])        # (n, d)
        h_mat = _stack_embeddings([f.embedding for f in historical])    # (m, d)

        if q_mat.size == 0 or h_mat.size == 0:
            return

        # Cosine similarity matrix (n x m)
        sim = _cosine_similarity_matrix(q_mat, h_mat)  # values in [-1, 1], we expect non-negative if embeddings are normalized upstream

        # For each query, take best historical match
        best_idx = sim.argmax(axis=1)
        best_scores = sim[np.arange(sim.shape[0]), best_idx]

        for i, score in enumerate(best_scores):
            if float(score) >= float(threshold):
                h = historical[int(best_idx[i])]
                items[i].answer = h.value

    def _generate_ai_answers_for_unanswered(self, items: List[FormItem]) -> List[Dict[str, str]]:
        """
        Calls AI service for only unanswered items. Returns AI-produced answers
        as a list of dicts with keys: label, answer, embeddings (optional).
        """
        unanswered = [ {"label": i.label, "answer": "", "embeddings": i.embeddings} for i in items if not i.answer ]
        if not unanswered:
            return []
        return AIService.ask_form_answers(unanswered)

    @staticmethod
    def _merge_ai_answers(items: List[FormItem], ai_answers: List[Dict[str, str]]) -> None:
        """
        Merge AI answers into items in-place by label.
        """
        if not ai_answers:
            return
        lookup = {a["label"]: a.get("answer", "") for a in ai_answers}
        for item in items:
            if not item.answer and item.label in lookup:
                item.answer = lookup[item.label]


# ---------------------------
# Numeric utilities
# ---------------------------

def _stack_embeddings(blobs: Iterable[bytes]) -> np.ndarray:
    """
    From an iterable of float32 byte blobs -> (N, D) float32 array.
    Returns empty (0, 0) if no embeddings.
    """
    arrays: List[np.ndarray] = []
    for b in blobs:
        arr = np.frombuffer(b, dtype=np.float32)
        arrays.append(arr)
    if not arrays:
        return np.empty((0, 0), dtype=np.float32)
    # Validate consistent dimensionality; if not, skip mismatched rows.
    dim = arrays[0].shape[0]
    filtered = [a for a in arrays if a.shape[0] == dim]
    if not filtered:
        return np.empty((0, 0), dtype=np.float32)
    return np.vstack(filtered).astype(np.float32, copy=False)


def _cosine_similarity_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Computes pairwise cosine similarity between rows of A (n x d) and B (m x d) -> (n x m).
    Handles zero vectors safely (returns 0 similarity for those rows).
    """
    # Normalize rows
    A_norms = np.linalg.norm(A, axis=1, keepdims=True)
    B_norms = np.linalg.norm(B, axis=1, keepdims=True)

    # Prevent division by zero
    A_safe = np.divide(A, A_norms, out=np.zeros_like(A), where=(A_norms != 0))
    B_safe = np.divide(B, B_norms, out=np.zeros_like(B), where=(B_norms != 0))

    # Cosine similarity
    return A_safe @ B_safe.T
