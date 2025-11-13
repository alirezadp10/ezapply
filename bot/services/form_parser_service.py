import re

from loguru import logger
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from bot.enums import ElementsEnum
from bot.helpers.helpers import find_elements


class FormParserService:
    def __init__(self, driver):
        self.driver = driver

    def parse_form_fields(self):
        """Parse visible and enabled input, select, textarea, checkbox, and radio fields from the modal form."""
        try:
            modal = find_elements(driver=self.driver, by=By.CSS_SELECTOR, selector=ElementsEnum.MODAL, retries=5, index=0)
        except NoSuchElementException:
            logger.error("❌ could not find modal element")
            return []

        form = next(iter(modal.find_elements(By.TAG_NAME, ElementsEnum.FORM)), None)
        if not form:
            return []

        fields = (
            self._extract_fields(
                form, ElementsEnum.INPUT_NOT_RADIO, self._should_include_input
            )
            + self._extract_fields(
                form,
                ElementsEnum.SELECT,
                self._should_include_select,
                include_options=True,
            )
            + self.extract_textareas(form)
            + self.extract_checkboxes(form)
            + self._extract_radios(form)
        )

        return fields

    # ---------------------------
    # Generic field extraction
    # ---------------------------

    def _extract_fields(self, form, selector, include_fn, include_options=False):
        """Generic field extractor for inputs and selects."""
        results = []
        for el in form.find_elements(By.CSS_SELECTOR, selector):
            if not include_fn(el):
                continue

            field_id = el.get_attribute("id")
            label = self._get_label(form, field_id)

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

    # ---------------------------
    # Textarea extraction
    # ---------------------------

    def extract_textareas(self, form):
        """Extracts visible and enabled multiline text fields."""
        results = []
        for el in form.find_elements(By.CSS_SELECTOR, ElementsEnum.TEXTAREA):
            if not (el.is_displayed() and el.is_enabled()):
                continue
            if el.get_attribute("value"):
                continue

            field_id = el.get_attribute("id")
            label = self._get_label(form, field_id)
            if not label:
                label = el.get_attribute("aria-label") or ""
            label = self.clean_label_text(label)
            results.append({"id": field_id, "label": label})
        return results

    # ---------------------------
    # Checkbox (multi-select) extraction
    # ---------------------------

    def extract_checkboxes(self, form):
        """Extracts multiple-choice checkbox groups (e.g., LinkedIn Easy Apply multi-select questions)."""
        results = []
        # Fieldsets with checkboxes — commonly identified by data-test-checkbox-form-component
        for fs in form.find_elements(
            By.CSS_SELECTOR, ElementsEnum.CHECKBOX_FIELDSET_COMPONENT
        ):
            if not fs.is_displayed():
                continue

            checkboxes = fs.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_CHECKBOX)
            if not checkboxes:
                continue

            # Extract main question label (legend text)
            label = self._extract_legend_text(fs)

            # Extract option labels
            options = []
            for cb in checkboxes:
                if not (cb.is_displayed() and cb.is_enabled()):
                    continue
                try:
                    sel = ElementsEnum.LABEL_FOR_TEMPLATE.format(
                        id=cb.get_attribute("id")
                    )
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

    # ---------------------------
    # Field-specific inclusion rules
    # ---------------------------

    def _should_include_input(self, el):
        return el.is_displayed() and el.is_enabled() and not el.get_attribute("value")

    def _should_include_select(self, el):
        if not el.is_displayed() or not el.is_enabled():
            return False
        value = (el.get_attribute("value") or "").strip()
        return not value or value == "Select an option"

    # ---------------------------
    # Radio extraction
    # ---------------------------

    def _extract_radios(self, form):
        """Extract radio button fieldsets and their labels/options."""
        results = []
        for fs in form.find_elements(By.CSS_SELECTOR, ElementsEnum.FIELDSET):
            if not fs.is_displayed():
                continue

            radios = fs.find_elements(By.CSS_SELECTOR, ElementsEnum.INPUT_RADIO)
            if not radios:
                continue

            label = self._extract_legend_text(fs)
            options = self._extract_radio_options(fs, radios)

            if options:
                label = f"{label} ({', '.join(options)})"

            results.append(
                {
                    "id": fs.get_attribute("id"),
                    "label": label,
                }
            )
        return results

    def _extract_legend_text(self, fieldset):
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
        return self.clean_label_text(legend)

    def _extract_radio_options(self, fieldset, radios):
        """Extract radio option labels."""
        options = []
        for radio in radios:
            if not (radio.is_displayed() and radio.is_enabled()):
                continue
            try:
                sel = ElementsEnum.LABEL_FOR_TEMPLATE.format(
                    id=radio.get_attribute("id")
                )
                label_el = fieldset.find_element(By.CSS_SELECTOR, sel)
                if label_el.text.strip():
                    options.append(label_el.text.strip())
            except Exception:
                continue
        return options

    # ---------------------------
    # Label cleaning utilities
    # ---------------------------

    def _get_label(self, form, field_id):
        """Get label text by field ID and clean it."""
        try:
            sel = ElementsEnum.LABEL_FOR_TEMPLATE.format(id=field_id)
            text = form.find_element(By.CSS_SELECTOR, sel).text
        except Exception:
            text = ""
        return self.clean_label_text(text)

    def clean_label_text(self, text):
        """Normalize whitespace and remove redundant or 'Required' text."""
        text = re.sub(r"\bRequired\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text.strip())

        # Deduplicate immediate phrase repetition
        text = re.sub(r"(?i)(?<!\S)(.+?)(?:\s+\1)+(?!\S)", r"\1", text)

        # Deduplicate repeated sentences or fragments
        seen, unique_parts = set(), []
        for part in re.split(r"(?<=[.?!])\s+|\n+", text):
            cleaned = part.strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                unique_parts.append(cleaned)

        return " ".join(unique_parts)
