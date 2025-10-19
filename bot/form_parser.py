import time

from loguru import logger
from selenium.webdriver.common.by import By


class FormParser:
    def __init__(self, driver):
        self.driver = driver

    def parse_form_fields(self):
        fields = []
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, 'div[data-test-modal]')
            form = modal.find_element(By.TAG_NAME, "form")
            fields += self.extract_inputs(form)
            fields += self.extract_selects(form)
        except Exception as e:
            logger.warning(f"⚠️ Error parsing form: {e}")
        return fields

    def extract_inputs(self, form):
        results = []
        for el in form.find_elements(By.CSS_SELECTOR, 'input:not([type="radio"])'):
            if not el.is_displayed() or not el.is_enabled():
                continue
            if el.get_attribute("value"):
                continue
            label = self._get_label(form, el.get_attribute("id"))
            results.append({"id": el.get_attribute("id"), "label": label})
        return results

    def extract_selects(self, form):
        results = []
        for el in form.find_elements(By.CSS_SELECTOR, "select"):
            if not el.is_displayed() or not el.is_enabled():
                continue
            if el.get_attribute("value").strip():
                continue
            label = self._get_label(form, el.get_attribute("id"))
            results.append({"id": el.get_attribute("id"), "label": label})
        return results

    def _get_label(self, form, field_id):
        try:
            label = form.find_element(By.CSS_SELECTOR, f'label[for="{field_id}"]').text.strip()
            return label
        except Exception:
            return ""
