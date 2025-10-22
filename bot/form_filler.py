from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

class FormFiller:
    def __init__(self, driver, wait_seconds: int = 10):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_seconds)

    def fill_fields(self, fields, answers) -> list:
        result = []

        for item in fields:
            # Wait for the element to exist to reduce flakiness
            el = self.wait.until(EC.presence_of_element_located((By.ID, item["id"])))

            # Resolve answer for this label
            answer = next((a["answer"] for a in answers if a["label"] == item["label"]), None)

            # Infer a meaningful "type" for result reporting
            tag = el.tag_name.lower()
            input_type_attr = (el.get_attribute("type") or "").lower()
            inferred_type = input_type_attr or tag

            # Special-case: fieldset that contains radios -> treat as "radio"
            if tag == "fieldset":
                has_radio = len(el.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')) > 0
                if has_radio:
                    inferred_type = "radio"

            result.append({"label": item["label"], "value": answer, "type": inferred_type})

            # If no answer provided, skip interaction but keep result record
            if answer in (None, ""):
                continue

            # Handle elements
            if tag == "input":
                if input_type_attr in ("checkbox",):
                    # For a single checkbox, accept true/false/yes/no/1/0
                    truthy = {"true", "yes", "1", "on"}
                    should_check = str(answer).strip().lower() in truthy
                    is_checked = el.is_selected()
                    if should_check != is_checked:
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        el.click()
                elif input_type_attr in ("radio",):
                    # Bare radio (not in a fieldset, rare but possible)
                    # Click it only if its value matches the answer
                    val = (el.get_attribute("value") or "").strip().lower()
                    if val == str(answer).strip().lower():
                        if not el.is_selected():
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                            el.click()
                else:
                    # Text-like inputs
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    el.clear()
                    el.send_keys(str(answer))

            elif tag == "select":
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    Select(el).select_by_visible_text(str(answer))
                except Exception:
                    # Fallback to value match if visible text doesn't work
                    Select(el).select_by_value(str(answer))

            elif tag == "textarea":
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                el.clear()
                el.send_keys(str(answer))

            elif tag == "fieldset":
                # Handle radio groups (your LinkedIn Easy Apply example)
                clicked = self._click_radio_in_fieldset(el, str(answer))
                if not clicked:
                    # Optional: log/debug when no radio matched
                    pass

            else:
                # Generic fallback: try to type into contenteditable or input-like children
                try:
                    editable = el.find_element(By.CSS_SELECTOR, '[contenteditable="true"]')
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", editable)
                    editable.clear()
                    editable.send_keys(str(answer))
                except Exception:
                    # No-op if not supported
                    pass

        return result

    def _click_radio_in_fieldset(self, fieldset, answer: str) -> bool:
        if not answer:
            return False

        radios = fieldset.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        answer_norm = str(answer).strip().lower()

        def click_via_label(radio) -> bool:
            rid = radio.get_attribute("id")
            if not rid:
                return False
            try:
                label = fieldset.find_element(By.CSS_SELECTOR, f"label[for='{rid}']")
            except Exception:
                return False

            # Scroll the label (not the input) into view and click it
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", label
            )
            try:
                self.wait.until(EC.element_to_be_clickable(label)).click()
            except ElementClickInterceptedException:
                # If still intercepted, try JS click on the label
                self.driver.execute_script("arguments[0].click();", label)
            except TimeoutException:
                # Last resort: JS click without clickability wait
                self.driver.execute_script("arguments[0].click();", label)
            return True

        # 1) Prefer exact value match
        for r in radios:
            val = (r.get_attribute("value") or "").strip().lower()
            if val == answer_norm:
                if r.is_selected():
                    return True
                # Try clicking the label first (it’s the thing intercepting clicks anyway)
                if click_via_label(r):
                    return True
                # Fallbacks if no label found
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", r
                    )
                    self.wait.until(EC.element_to_be_clickable(r)).click()
                except ElementClickInterceptedException:
                    # JS click the input
                    self.driver.execute_script("arguments[0].click();", r)
                except TimeoutException:
                    # Focus + SPACE as last fallback
                    self.driver.execute_script("arguments[0].focus();", r)
                    r.send_keys(Keys.SPACE)
                return True

        # 2) Match by label text (exact)
        labels = {
            lab.get_attribute("for"): (lab, (lab.text or "").strip().lower())
            for lab in fieldset.find_elements(By.TAG_NAME, "label")
            if lab.get_attribute("for")
        }
        for r in radios:
            rid = r.get_attribute("id")
            if rid in labels and labels[rid][1] == answer_norm:
                if r.is_selected():
                    return True
                # Click the label
                label = labels[rid][0]
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", label
                )
                try:
                    self.wait.until(EC.element_to_be_clickable(label)).click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", label)
                except TimeoutException:
                    self.driver.execute_script("arguments[0].click();", label)
                return True

        # 3) Match by label text (contains) — for options like “Yes, within 30 minutes”
        for r in radios:
            rid = r.get_attribute("id")
            if rid in labels and answer_norm in labels[rid][1]:
                label = labels[rid][0]
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", label
                )
                try:
                    self.wait.until(EC.element_to_be_clickable(label)).click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", label)
                except TimeoutException:
                    self.driver.execute_script("arguments[0].click();", label)
                return True

        return False
