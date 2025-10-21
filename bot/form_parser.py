from selenium.webdriver.common.by import By
import re


class FormParser:
    def __init__(self, driver):
        self.driver = driver

    def parse_form_fields(self):
        fields = []
        modal = self.driver.find_element(By.CSS_SELECTOR, 'div[data-test-modal]')
        if modal.find_elements(By.TAG_NAME, "form"):
            form = modal.find_element(By.TAG_NAME, "form")
            fields += self.extract_inputs(form)
            fields += self.extract_selects(form)
            fields += self.extract_radios(form)
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
            if el.get_attribute("value").strip() and el.get_attribute("value").strip() != "Select an option":
                continue

            label = self._get_label(form, el.get_attribute("id"))

            options = [
                opt.text.strip()
                for opt in el.find_elements(By.TAG_NAME, "option")
                if opt.text.strip()
            ]

            label = f"{label} ({', '.join(options)})" if options else label

            # Store results
            results.append({
                "id": el.get_attribute("id"),
                "label": label,
            })

        return results

    def extract_radios(self, form):
        results = []
        # Find all fieldsets that contain radio buttons
        for fs in form.find_elements(By.CSS_SELECTOR, 'fieldset'):
            # Skip if no radio inputs inside
            radios = fs.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            if not radios:
                continue
            if not fs.is_displayed():
                continue

            # Extract the question/label text from legend
            label = ""
            try:
                legend_el = fs.find_element(By.TAG_NAME, "legend")
                label = legend_el.text.strip()
                # Clean up extra whitespace and remove "Required"
                label = re.sub(r"\bRequired\b", "", label).strip()
            except Exception:
                pass

            # Extract all radio options
            options = []
            for radio in radios:
                if not radio.is_displayed() or not radio.is_enabled():
                    continue
                try:
                    label_el = fs.find_element(By.CSS_SELECTOR, f'label[for="{radio.get_attribute("id")}"]')
                    if label_el and label_el.text.strip():
                        options.append(label_el.text.strip())
                except Exception:
                    pass

            # Build the final label text like the select version
            if options:
                label = f"{label} ({', '.join(options)})"

            results.append({
                "id": fs.get_attribute("id"),
                "label": label,
            })

        return results

    def _get_label(self, form, field_id):
        """
        Extracts label text for a given field ID and removes duplicates / extra whitespace.
        Works for both <label for="..."> and fallback cases.
        """
        try:
            label = form.find_element(By.CSS_SELECTOR, f'label[for="{field_id}"]').text
        except Exception:
            label = ""

        # Clean text and remove duplicates
        label = self.clean_label_text(label)
        return label


    def clean_label_text(self, text):
        """Normalizes whitespace, removes duplicate lines/sentences, and strips junk like 'Required'."""
        text = re.sub(r"\bRequired\b", "", text, flags=re.IGNORECASE)
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # normalize whitespace

        # Split on either sentence boundaries or newlines
        parts = re.split(r'(?<=[.?!])\s+|\n+', text)

        seen = set()
        unique_parts = []
        for part in parts:
            cleaned = part.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                unique_parts.append(cleaned)

        return " ".join(unique_parts)