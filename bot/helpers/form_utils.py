# bot/helpers/form_utils.py

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Set, Tuple

from selenium.common import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from bot.enums import ElementsEnum

# ==========================================
# Label / text cleaning
# ==========================================

def clean_label_text(text: str) -> str:
    """Normalize whitespace and remove redundant or 'Required' text."""
    text = re.sub(r"\bRequired\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text.strip())

    # Deduplicate immediate phrase repetition
    text = re.sub(r"(?i)(?<!\S)(.+?)(?:\s+\1)+(?!\S)", r"\1", text)

    # Deduplicate repeated sentences or fragments
    seen: Set[str] = set()
    unique_parts: List[str] = []
    for part in re.split(r"(?<=[.?!])\s+|\n+", text):
        cleaned = part.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            unique_parts.append(cleaned)

    return " ".join(unique_parts)


def get_label(form: WebElement, field_id: str) -> str:
    """Get label text by field ID and clean it."""
    try:
        sel = ElementsEnum.LABEL_FOR_TEMPLATE.format(id=field_id)
        text = form.find_element(By.CSS_SELECTOR, sel).text
    except Exception:
        text = ""
    return clean_label_text(text)


# ==========================================
# Inclusion rules
# ==========================================

def should_include_input(el: WebElement) -> bool:
    return el.is_displayed() and el.is_enabled() and not el.get_attribute("value")


def should_include_select(el: WebElement) -> bool:
    if not el.is_displayed() or not el.is_enabled():
        return False
    value = (el.get_attribute("value") or "").strip()
    return not value or value == "Select an option"


# ==========================================
# Generic field extraction
# ==========================================

def extract_fields(
        form: WebElement,
        selector: str,
        include_fn,
        *,
        include_options: bool = False,
) -> List[Dict[str, str]]:
    """Generic field extractor for inputs and selects."""
    results: List[Dict[str, str]] = []
    for el in form.find_elements(By.CSS_SELECTOR, selector):
        if not include_fn(el):
            continue

        field_id = el.get_attribute("id")
        label = get_label(form, field_id)

        if include_options:
            options = [
                opt.text.strip()
                for opt in el.find_elements(By.TAG_NAME, ElementsEnum.OPTION)
                if opt.text.strip()
            ]
            if options:
                label = f"{label} ({', '.join(options)})"

        results.append({"id": field_id, "label": label})
    return results


def extract_textareas(form: WebElement) -> List[Dict[str, str]]:
    """Extracts visible and enabled multiline text fields."""
    results: List[Dict[str, str]] = []
    for el in form.find_elements(By.CSS_SELECTOR, ElementsEnum.TEXTAREA):
        if not (el.is_displayed() and el.is_enabled()):
            continue
        if el.get_attribute("value"):
            continue

        field_id = el.get_attribute("id")
        label = get_label(form, field_id)
        if not label:
            label = el.get_attribute("aria-label") or ""
        label = clean_label_text(label)
        results.append({"id": field_id, "label": label})
    return results


def extract_legend_text(fieldset: WebElement) -> str:
    """Extract and clean text from <legend> or its inner span(s)."""
    try:
        legend = fieldset.find_element(By.TAG_NAME, ElementsEnum.LEGEND).text
        if not legend.strip():
            # LinkedIn sometimes hides text in <span> elements
            legend = " ".join(
                span.text
                for span in fieldset.find_elements(By.TAG_NAME, ElementsEnum.SPAN)
                if span.text.strip()
            )
    except Exception:
        legend = ""
    return clean_label_text(legend)


def extract_checkbox_groups(form: WebElement) -> List[Dict[str, str]]:
    """Extracts multiple-choice checkbox groups (e.g., LinkedIn Easy Apply multi-select questions)."""
    results: List[Dict[str, str]] = []

    for fs in form.find_elements(By.CSS_SELECTOR, ElementsEnum.CHECKBOX_FIELDSET_COMPONENT):
        if not fs.is_displayed():
            continue

        checkboxes = fs.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX)
        if not checkboxes:
            continue

        # Extract main question label (legend text)
        label = extract_legend_text(fs)

        # Extract option labels
        options: List[str] = []
        for cb in checkboxes:
            if not (cb.is_displayed() and cb.is_enabled()):
                continue
            try:
                sel = ElementsEnum.LABEL_FOR_TEMPLATE.format(id=cb.get_attribute("id"))
                label_el = fs.find_element(By.CSS_SELECTOR, sel)
                if label_el.text.strip():
                    options.append(label_el.text.strip())
            except Exception:
                continue

        if options:
            label = f"{label} ({', '.join(options)})"

        results.append(
            {
                "id": fs.get_attribute("id"),
                "label": label,
            }
        )
    return results


def extract_radio_options(fieldset: WebElement, radios: Iterable[WebElement]) -> List[str]:
    """Extract radio option labels."""
    options: List[str] = []
    for radio in radios:
        if not (radio.is_displayed() and radio.is_enabled()):
            continue
        try:
            sel = ElementsEnum.LABEL_FOR_TEMPLATE.format(id=radio.get_attribute("id"))
            label_el = fieldset.find_element(By.CSS_SELECTOR, sel)
            if label_el.text.strip():
                options.append(label_el.text.strip())
        except Exception:
            continue
    return options


def extract_radio_groups(form: WebElement) -> List[Dict[str, str]]:
    """Extract radio button fieldsets and their labels/options."""
    results: List[Dict[str, str]] = []
    for fs in form.find_elements(By.CSS_SELECTOR, ElementsEnum.FIELDSET):
        if not fs.is_displayed():
            continue

        radios = fs.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO)
        if not radios:
            continue

        label = extract_legend_text(fs)
        options = extract_radio_options(fs, radios)

        if options:
            label = f"{label} ({', '.join(options)})"

        results.append(
            {
                "id": fs.get_attribute("id"),
                "label": label,
            }
        )
    return results


# ==========================================
# Utilities
# ==========================================

def wait_present_by_id(wait: WebDriverWait, element_id: str) -> WebElement:
    return wait.until(ec.presence_of_element_located((By.ID, element_id)))


def scroll_into_view(driver, el: WebElement) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)


def is_truthy(value: Any) -> bool:
    truthy: Set[str] = {"true", "yes", "1", "on"}
    return str(value).strip().lower() in truthy


def normalize_multi_answer(answer: Any) -> Set[str]:
    if isinstance(answer, (list, tuple, set)):
        return {str(a).strip().lower() for a in answer if str(a).strip()}
    # allow comma or semicolon separated strings
    text = str(answer)
    chunks = [x.strip() for x in text.replace(";", ",").split(",")]
    return {c.lower() for c in chunks if c}


def infer_type(el: WebElement) -> str:
    tag = el.tag_name.lower()
    input_type_attr = (el.get_attribute("type") or "").lower()
    inferred_type = input_type_attr or tag

    if tag == "fieldset":
        if el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO):
            inferred_type = "radio"
        elif el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX):
            inferred_type = "checkbox-group"
    return inferred_type


# ==========================================
# Fieldset helpers
# ==========================================

def _click_radio_via_label(
        driver,
        wait: WebDriverWait,
        fieldset: WebElement,
        radio: WebElement,
) -> bool:
    rid = radio.get_attribute("id")
    if not rid:
        return False
    try:
        label = fieldset.find_element(By.CSS_SELECTOR, f"label[for='{rid}']")
    except Exception:
        return False

    scroll_into_view(driver, label)
    try:
        wait.until(ec.element_to_be_clickable(label)).click()
    except (ElementClickInterceptedException, TimeoutException):
        driver.execute_script("arguments[0].click();", label)
    return True


def click_radio_in_fieldset(
        driver,
        wait: WebDriverWait,
        fieldset: WebElement,
        answer: str,
) -> bool:
    if not answer:
        return False

    radios = fieldset.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO)
    answer_norm = answer.strip().lower()

    # 1) Match by radio value
    for r in radios:
        val = (r.get_attribute("value") or "").strip().lower()
        if val == answer_norm:
            if r.is_selected():
                return True
            if _click_radio_via_label(driver, wait, fieldset, r):
                return True
            try:
                scroll_into_view(driver, r)
                wait.until(ec.element_to_be_clickable(r)).click()
            except (ElementClickInterceptedException, TimeoutException):
                try:
                    driver.execute_script("arguments[0].click();", r)
                except Exception:
                    driver.execute_script("arguments[0].focus();", r)
                    r.send_keys(Keys.SPACE)
            return True

    # Build label map once
    labels: Dict[str, Tuple[WebElement, str]] = {
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
            scroll_into_view(driver, label)
            try:
                wait.until(ec.element_to_be_clickable(label)).click()
            except (ElementClickInterceptedException, TimeoutException):
                driver.execute_script("arguments[0].click();", label)
            return True

    # 3) Contains label text match
    for r in radios:
        rid = r.get_attribute("id")
        if rid in labels and answer_norm in labels[rid][1]:
            label = labels[rid][0]
            scroll_into_view(driver, label)
            try:
                wait.until(ec.element_to_be_clickable(label)).click()
            except (ElementClickInterceptedException, TimeoutException):
                driver.execute_script("arguments[0].click();", label)
            return True

    return False


def _click_checkbox_label(
        driver,
        wait: WebDriverWait,
        labels: Dict[str, Tuple[WebElement, str]],
        input_el: WebElement,
) -> bool:
    rid = input_el.get_attribute("id")
    if not rid or rid not in labels:
        return False
    label_el = labels[rid][0]
    scroll_into_view(driver, label_el)
    try:
        wait.until(ec.element_to_be_clickable(label_el)).click()
    except (ElementClickInterceptedException, TimeoutException):
        driver.execute_script("arguments[0].click();", label_el)
    return True


def set_checkboxes_in_fieldset(
        driver,
        wait: WebDriverWait,
        fieldset: WebElement,
        answer: Any,
        *,
        unselect_others: bool = False,
) -> bool:
    if answer is None or str(answer).strip() == "":
        return False

    desired = normalize_multi_answer(answer)
    checkboxes = fieldset.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX)

    labels: Dict[str, Tuple[WebElement, str]] = {
        lab.get_attribute("for"): (lab, (lab.text or "").strip().lower())
        for lab in fieldset.find_elements(By.TAG_NAME, ElementsEnum.LABEL)
        if lab.get_attribute("for")
    }

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
                if not _click_checkbox_label(driver, wait, labels, cb):
                    scroll_into_view(driver, cb)
                    try:
                        wait.until(ec.element_to_be_clickable(cb)).click()
                    except (ElementClickInterceptedException, TimeoutException):
                        driver.execute_script("arguments[0].click();", cb)
                changed = True

    # Optionally uncheck everything else
    if unselect_others:
        for cb in checkboxes:
            val = (cb.get_attribute("value") or "").strip().lower()
            rid = cb.get_attribute("id")
            label_txt = labels.get(rid, (None, ""))[1] if rid in labels else ""

            is_desired = (
                    (val in desired)
                    or (label_txt in desired)
                    or any(w in label_txt for w in desired if len(w) >= 3)
            )
            if cb.is_selected() and not is_desired:
                if not _click_checkbox_label(driver, wait, labels, cb):
                    scroll_into_view(driver, cb)
                    try:
                        wait.until(ec.element_to_be_clickable(cb)).click()
                    except (ElementClickInterceptedException, TimeoutException):
                        driver.execute_script("arguments[0].click();", cb)
                changed = True

    return seen_target or changed


# ==========================================
# Element handlers
# ==========================================

def handle_input(driver, el: WebElement, answer: Any) -> None:
    input_type = (el.get_attribute("type") or "").lower()

    if input_type == "checkbox":
        should_check = is_truthy(answer)
        if should_check != el.is_selected():
            scroll_into_view(driver, el)
            el.click()
        return

    if input_type == "radio":
        # Rare: bare radio not inside fieldset
        val = (el.get_attribute("value") or "").strip().lower()
        if val == str(answer).strip().lower() and not el.is_selected():
            scroll_into_view(driver, el)
            el.click()
        return

    # Text-like inputs (text, email, date, number, etc.)
    scroll_into_view(driver, el)
    el.clear()
    el.send_keys(str(answer))

    # Quirk: close potential role=combobox overlay if present
    if el.get_attribute("role") == ElementsEnum.ROLE_COMBOBOX:
        try:
            driver.find_element(By.CSS_SELECTOR, ElementsEnum.MODAL).click()
        except Exception:
            pass


def handle_select(driver, el: WebElement, answer: Any) -> None:
    scroll_into_view(driver, el)
    sel = Select(el)
    ans = str(answer)
    try:
        sel.select_by_visible_text(ans)
    except Exception:
        sel.select_by_value(ans)


def handle_textarea(driver, el: WebElement, answer: Any) -> None:
    scroll_into_view(driver, el)
    el.clear()
    el.send_keys(str(answer))


def handle_fieldset(driver, wait: WebDriverWait, el: WebElement, answer: Any) -> None:
    has_radio = el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO)
    has_checkbox = el.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX)

    if has_radio:
        click_radio_in_fieldset(driver, wait, el, str(answer))
    elif has_checkbox:
        set_checkboxes_in_fieldset(driver, wait, el, answer, unselect_others=False)


def handle_generic_editable(driver, el: WebElement, answer: Any) -> None:
    # Fallback for contenteditable or nested input-like areas
    try:
        editable = el.find_element(By.CSS_SELECTOR, ElementsEnum.CONTENTEDITABLE)
        scroll_into_view(driver, editable)
        editable.clear()
        editable.send_keys(str(answer))
    except Exception:
        # No-op if not supported
        pass
