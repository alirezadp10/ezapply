from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait

from bot.enums import ElementsEnum
from bot.schemas import FormItemSchema


class FormFillerService:
    def __init__(self, driver, wait_seconds: int = 10):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_seconds)

    # -----------------------------
    # Public API
    # -----------------------------
    def fill_fields(self, fields: Iterable[Dict[str, Any]], answers: Iterable[FormItemSchema]) -> List[FormItemSchema]:
        """
        Fill collection of form fields using (label -> answer) pairs.

        Returns a list of {"label": str, "value": Any, "type": str} rows describing what was attempted.
        """
        result: List[FormItemSchema] = []
        answer_map = {str(a.label): a.answer for a in answers}

        for item in fields:
            field_id = item["id"]
            label = item["label"]

            el = self._wait_present_by_id(field_id)

            inferred_type = self._infer_type(el)
            answer = answer_map.get(label)

            result.append(FormItemSchema(label=label, answer=answer, type=inferred_type))

            # Skip if no provided answer, but still report in result
            if answer in (None, ""):
                continue

            tag = el.tag_name.lower()

            if tag == "input":
                self._handle_input(el, answer)
            elif tag == "select":
                self._handle_select(el, answer)
            elif tag == "textarea":
                self._handle_textarea(el, answer)
            elif tag == "fieldset":
                self._handle_fieldset(el, answer)
            else:
                self._handle_generic_editable(el, answer)

        return result

    # -----------------------------
    # Element handlers
    # -----------------------------
    def _handle_input(self, el: WebElement, answer: Any) -> None:
        input_type = (el.get_attribute("type") or "").lower()

        if input_type == "checkbox":
            should_check = self._is_truthy(answer)
            if should_check != el.is_selected():
                self._scroll_into_view(el)
                el.click()
            return

        if input_type == "radio":
            # Rare: bare radio not inside fieldset
            val = (el.get_attribute("value") or "").strip().lower()
            if val == str(answer).strip().lower() and not el.is_selected():
                self._scroll_into_view(el)
                el.click()
            return

        # Text-like inputs (text, email, date, number, etc.)
        self._scroll_into_view(el)
        el.clear()
        el.send_keys(str(answer))

        # Quirk: close potential role=combobox overlay if present
        if el.get_attribute("role") == ElementsEnum.ROLE_COMBOBOX:
            try:
                self.driver.find_element(By.CSS_SELECTOR, ElementsEnum.MODAL).click()
            except Exception:
                pass

    def _handle_select(self, el: WebElement, answer: Any) -> None:
        self._scroll_into_view(el)
        sel = Select(el)
        ans = str(answer)
        try:
            sel.select_by_visible_text(ans)
        except Exception:
            sel.select_by_value(ans)

    def _handle_textarea(self, el: WebElement, answer: Any) -> None:
        self._scroll_into_view(el)
        el.clear()
        el.send_keys(str(answer))

    def _handle_fieldset(self, el: WebElement, answer: Any) -> None:
        has_radio = el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO)
        has_checkbox = el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX)

        if has_radio:
            self._click_radio_in_fieldset(el, str(answer))
        elif has_checkbox:
            self._set_checkboxes_in_fieldset(el, answer, unselect_others=False)

    def _handle_generic_editable(self, el: WebElement, answer: Any) -> None:
        # Fallback for contenteditable or nested input-like areas
        try:
            editable = el.find_element(By.CSS_SELECTOR, ElementsEnum.CONTENTEDITABLE)
            self._scroll_into_view(editable)
            editable.clear()
            editable.send_keys(str(answer))
        except Exception:
            # No-op if not supported
            pass

    # -----------------------------
    # Fieldset helpers (kept behavior, cleaned a bit)
    # -----------------------------
    def _click_radio_in_fieldset(self, fieldset: WebElement, answer: str) -> bool:
        if not answer:
            return False

        radios = fieldset.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO)
        answer_norm = answer.strip().lower()

        def click_via_label(radio: WebElement) -> bool:
            rid = radio.get_attribute("id")
            if not rid:
                return False
            try:
                label = fieldset.find_element(By.CSS_SELECTOR, f"label[for='{rid}']")
            except Exception:
                return False

            self._scroll_into_view(label)
            try:
                self.wait.until(ec.element_to_be_clickable(label)).click()
            except (ElementClickInterceptedException, TimeoutException):
                self.driver.execute_script("arguments[0].click();", label)
            return True

        # 1) Match by radio value
        for r in radios:
            val = (r.get_attribute("value") or "").strip().lower()
            if val == answer_norm:
                if r.is_selected():
                    return True
                if click_via_label(r):
                    return True
                try:
                    self._scroll_into_view(r)
                    self.wait.until(ec.element_to_be_clickable(r)).click()
                except (ElementClickInterceptedException, TimeoutException):
                    try:
                        self.driver.execute_script("arguments[0].click();", r)
                    except Exception:
                        self.driver.execute_script("arguments[0].focus();", r)
                        r.send_keys(Keys.SPACE)
                return True

        # Build label map once
        labels: Dict[str, tuple[WebElement, str]] = {
            lab.get_attribute("for"): (lab, (lab.text or "").strip().lower())
            for lab in fieldset.find_elements(By.TAG_NAME, ElementsEnum.LABEL)
            if lab.get_attribute("for")
        }

        # 2) Exact label text match
        for r in radios:
            rid = r.get_attribute("id")
            if rid in labels and labels[rid][1] == answer_norm:
                if r.is_selected():
                    return True
                label = labels[rid][0]
                self._scroll_into_view(label)
                try:
                    self.wait.until(ec.element_to_be_clickable(label)).click()
                except (ElementClickInterceptedException, TimeoutException):
                    self.driver.execute_script("arguments[0].click();", label)
                return True

        # 3) Contains label text match
        for r in radios:
            rid = r.get_attribute("id")
            if rid in labels and answer_norm in labels[rid][1]:
                label = labels[rid][0]
                self._scroll_into_view(label)
                try:
                    self.wait.until(ec.element_to_be_clickable(label)).click()
                except (ElementClickInterceptedException, TimeoutException):
                    self.driver.execute_script("arguments[0].click();", label)
                return True

        return False

    def _set_checkboxes_in_fieldset(self, fieldset: WebElement, answer: Any, unselect_others: bool = False) -> bool:
        if answer is None or str(answer).strip() == "":
            return False

        desired = self._normalize_multi_answer(answer)
        checkboxes = fieldset.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX)

        labels: Dict[str, tuple[WebElement, str]] = {
            lab.get_attribute("for"): (lab, (lab.text or "").strip().lower())
            for lab in fieldset.find_elements(By.TAG_NAME, ElementsEnum.LABEL)
            if lab.get_attribute("for")
        }

        def click_label_for(input_el: WebElement) -> bool:
            rid = input_el.get_attribute("id")
            if not rid or rid not in labels:
                return False
            label_el = labels[rid][0]
            self._scroll_into_view(label_el)
            try:
                self.wait.until(ec.element_to_be_clickable(label_el)).click()
            except (ElementClickInterceptedException, TimeoutException):
                self.driver.execute_script("arguments[0].click();", label_el)
            return True

        changed = False
        seen_target = False

        # Indexes for fast lookup
        by_value: Dict[str, List[WebElement]] = {}
        for cb in checkboxes:
            val = (cb.get_attribute("value") or "").strip().lower()
            by_value.setdefault(val, []).append(cb)

        by_label_text: Dict[str, List[WebElement]] = {}
        for cb in checkboxes:
            rid = cb.get_attribute("id")
            if rid and rid in labels:
                by_label_text.setdefault(labels[rid][1], []).append(cb)

        # Ensure desired are checked (value -> exact label -> contains in label)
        for want in desired:
            candidates = list(by_value.get(want, [])) or list(by_label_text.get(want, []))
            if not candidates:
                for label_txt, cbs in by_label_text.items():
                    if want in label_txt:
                        candidates.extend(cbs)

            if not candidates:
                continue

            seen_target = True
            for cb in candidates:
                if not cb.is_selected():
                    if not click_label_for(cb):
                        self._scroll_into_view(cb)
                        try:
                            self.wait.until(ec.element_to_be_clickable(cb)).click()
                        except (ElementClickInterceptedException, TimeoutException):
                            self.driver.execute_script("arguments[0].click();", cb)
                    changed = True

        # Optionally uncheck everything else
        if unselect_others:
            for cb in checkboxes:
                val = (cb.get_attribute("value") or "").strip().lower()
                rid = cb.get_attribute("id")
                label_txt = labels.get(rid, (None, ""))[1] if rid in labels else ""

                is_desired = (
                    (val in desired) or (label_txt in desired) or any(w in label_txt for w in desired if len(w) >= 3)
                )
                if cb.is_selected() and not is_desired:
                    if not click_label_for(cb):
                        self._scroll_into_view(cb)
                        try:
                            self.wait.until(ec.element_to_be_clickable(cb)).click()
                        except (ElementClickInterceptedException, TimeoutException):
                            self.driver.execute_script("arguments[0].click();", cb)
                    changed = True

        return seen_target or changed

    # -----------------------------
    # Utilities
    # -----------------------------
    def _wait_present_by_id(self, element_id: str) -> WebElement:
        return self.wait.until(ec.presence_of_element_located((By.ID, element_id)))

    def _scroll_into_view(self, el: WebElement) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)

    def _is_truthy(self, value: Any) -> bool:
        truthy: Set[str] = {"true", "yes", "1", "on"}
        return str(value).strip().lower() in truthy

    def _normalize_multi_answer(self, answer: Any) -> Set[str]:
        if isinstance(answer, (list, tuple, set)):
            return {str(a).strip().lower() for a in answer if str(a).strip()}
        # allow comma or semicolon separated strings
        text = str(answer)
        chunks = [x.strip() for x in text.replace(";", ",").split(",")]
        return {c.lower() for c in chunks if c}

    def _infer_type(self, el: WebElement) -> str:
        tag = el.tag_name.lower()
        input_type_attr = (el.get_attribute("type") or "").lower()
        inferred_type = input_type_attr or tag

        if tag == "fieldset":
            if el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO):
                inferred_type = "radio"
            elif el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX):
                inferred_type = "checkbox-group"
        return inferred_type
