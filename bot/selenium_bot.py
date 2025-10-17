import re
import json
import requests
import time
from bot.config import settings
from bot.db_manager import DBManager
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from bot.enums import Country, WorkTypes
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


class SeleniumBot:
    def __init__(self, name: str, db_url: str):
        self.name = name
        self.driver = self.get_driver()
        self.db = DBManager(db_url)

    def get_driver(self):
        opts = Options()

        if settings.HEADLESS:
            opts.add_argument("--headless=new")

        opts.page_load_strategy = "none"  # 🚀 Don't wait for all resources

        opts.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 0,
        })

        opts.add_argument("user-data-dir=" + settings.USER_DATA_DIR)

        return webdriver.Chrome(options=opts)

    def run(self):
        logger.info("Ensuring login state...")
        self.ensure_logged_in()

        selected_countries = settings.COUNTRIES
        if not selected_countries:
            countries = [country.name for country in Country]
        else:
            countries = [c.strip().upper() for c in selected_countries.split(",") if c.strip()]

        keywords = settings.KEYWORDS.split(",")

        for country in countries:
            for keyword in keywords:
                url = self.build_job_url(keyword.strip(), Country[country].value)
                logger.info(f"Running job search for {keyword} in {country}")

                self.driver.get(url)
                time.sleep(settings.DELAY_TIME)

                for job_id in self.get_easy_apply_job_ids():
                    try:
                        self.apply_to_job(job_id, url)
                    except Exception as ex:
                        self.db.save_job(job_id=job_id, status="failed", url=f"{url}&currentJobId={job_id}")
                        logger.error(f"❌ Error applying for job {job_id}: {ex}")
                        continue

    def kill_driver(self):
        self.driver.quit()

    def ensure_logged_in(self):
        """Ensure the user is logged in to LinkedIn."""
        self.driver.get(f"{settings.LINKEDIN_BASE_URL}/login/fa")
        time.sleep(settings.DELAY_TIME)

        if any(keyword in self.driver.current_url for keyword in ("feed", "notifications")):
            logger.info("✅ Already logged in.")
            return

        self.driver.find_element(By.NAME, "session_key").send_keys(settings.LINKEDIN_USERNAME)
        self.driver.find_element(By.NAME, "session_password").send_keys(settings.LINKEDIN_PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, '[data-litms-control-urn="login-submit"]').click()

        WebDriverWait(self.driver, settings.DELAY_TIME).until(EC.url_contains("feed"))
        logger.info("✅ Login successful.")

    def build_job_url(self, keyword: str, country_id: int) -> str:
        """Build LinkedIn job search URL."""
        return f"{settings.LINKEDIN_BASE_URL}/jobs/search?keywords={keyword}&f_TPR=r{settings.JOB_SEARCH_TIME_WINDOW}&f_WT={WorkTypes(settings.WORK_TYPE)}&geoId={country_id}"

    def get_easy_apply_job_ids(self):
        """Return a list of Easy Apply job IDs."""
        return [
            int(div.get_attribute("data-job-id"))
            for div in self.driver.find_elements(By.CSS_SELECTOR, 'div[data-job-id]')
            if "Easy Apply" in div.text
        ]

    def apply_to_job(self, job_id: int, url: str):
        """Automate the Easy Apply process for a given job."""
        logger.info(f"🟩 Applying to job: {job_id}")

        if self.db.is_applied_for_job(job_id):
            return

        self.open_job_posting(job_id)
        self.click_apply_button()
    
        while True:
            if self.element_exists('[type="error-pebble-icon"]'):
                self.close_and_next(job_id, url)
                break

            if self.submit_if_ready(job_id):
                self.db.save_job(job_id=job_id, status="applied", url=f"{url}&currentJobId={job_id}")
                self.click_if_exists('[aria-label="Dismiss"]')
                break

            if self.handle_resume_step():
                continue

            payload = self.parse_form_fields()
            if payload:
                answers = self.ask_from_ai(payload)
                self.fill_form_fields(payload, answers)

            if self.next_step_or_review():
                continue

    def open_job_posting(self, job_id: int):
        """Open the job posting from the list."""
        self.driver.find_element(By.CSS_SELECTOR, f'div[data-job-id="{job_id}"]').click()
        time.sleep(settings.DELAY_TIME)

    def click_apply_button(self):
        """Click the 'Apply' button on a job listing."""
        self.driver.find_element(By.ID, "jobs-apply-button-id").click()
        time.sleep(settings.DELAY_TIME)

    def handle_resume_step(self):
        """Handle steps involving resume upload and continue."""
        if self.element_exists('span', 'Upload resume') and self.element_exists('[aria-label="Continue to next step"]'):
            self.click_if_exists('[aria-label="Continue to next step"]')
            return True
        return False

    def next_step_or_review(self):
        """Try to proceed to next step or review step."""
        return (
                self.click_if_exists('[aria-label="Continue to next step"]') or
                self.click_if_exists('[aria-label="Review your application"]')
        )

    def close_and_next(self, job_id: int, url):
        self.db.save_job(job_id=job_id, status="failed", url=f"{url}&currentJobId={job_id}")
        self.click_if_exists('[aria-label="Dismiss"]')
        self.click_if_exists('[data-control-name="discard_application_confirm_btn"]')
        time.sleep(settings.DELAY_TIME)

    def submit_if_ready(self, job_id: int):
        """Submit the application if ready and close dialogs."""
        if self.element_exists('span', 'Upload resume') and self.element_exists('[aria-label="Submit application"]'):
            self.click_if_exists('[aria-label="Submit application"]')
            self.finalize_submission(job_id)
            return True

        if self.click_if_exists('[aria-label="Submit application"]'):
            self.finalize_submission(job_id)
            return True

        return False

    def finalize_submission(self, job_id: int):
        """Finalize and confirm submission."""
        time.sleep(settings.DELAY_TIME)
        self.click_if_exists('[aria-label="Dismiss"]')
        print(f"✅ Submitted application for job {job_id}")
        time.sleep(settings.DELAY_TIME)

    def fill_form_fields(self, payload, answers):
        """Fill out form fields using AI-generated answers."""
        for item in payload:
            answer = self.get_answer_by_label(answers, item["label"])
            if not answer:
                continue

            try:
                input_el = self.driver.find_element(By.ID, item["id"])
                tag_name = input_el.tag_name.lower()
                input_type = (input_el.get_attribute("type") or "").lower()

                if tag_name == "input":
                    self.fill_input_field(input_el, input_type, answer)
                elif tag_name == "select":
                    self.fill_select_field(input_el, answer)
                elif tag_name == "textarea":
                    input_el.clear()
                    input_el.send_keys(answer)
                else:
                    print(f"⚠️ Unsupported tag: {tag_name} (id: {item['id']})")

            except Exception as e:
                print(f"⚠️ Error filling field {item['id']}: {e}")

    def fill_input_field(self, element, input_type, value):
        """Fill an <input> element based on its type."""
        if input_type in ["text", "email", "tel", "url", "number"]:
            element.clear()
            element.send_keys(value)
        elif input_type == "checkbox":
            should_check = value.strip().lower() in ["yes", "true", "1"]
            if element.is_selected() != should_check:
                element.click()
        else:
            print(f"⚠️ Unsupported input type: {input_type}")

    def fill_select_field(self, element, value):
        """Fill a <select> dropdown element."""
        select = Select(element)
        try:
            select.select_by_visible_text(value)
        except Exception:
            try:
                select.select_by_value(value)
            except Exception:
                print(f"⚠️ Could not select '{value}' for select id {element.get_attribute('id')}")

    def parse_form_fields(self):
        """Collect unfilled fields inside LinkedIn’s application modal."""
        fields = []
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, 'div[data-test-modal]')
            form = modal.find_element(By.TAG_NAME, "form")

            fields += self.extract_text_inputs(form)
            fields += self.extract_radio_groups(form)
            fields += self.extract_selects(form)

        except Exception as e:
            print(f"⚠️ Error parsing form: {e}")
        return fields

    def extract_text_inputs(self, form):
        """Extract all visible unfilled text inputs."""
        fields = []
        for input_el in form.find_elements(By.CSS_SELECTOR, 'input:not([type="radio"])'):
            if not input_el.is_displayed() or not input_el.is_enabled():
                continue
            if (input_el.get_attribute("value") or "").strip():
                continue

            label = self.extract_label_text(form, input_el.get_attribute("id"))
            fields.append({"id": input_el.get_attribute("id"), "label": label})
        return fields

    def extract_radio_groups(self, form):
        """Extract unfilled radio button groups."""
        fields = []
        for fs in form.find_elements(By.CSS_SELECTOR, 'fieldset[data-test-form-builder-radio-button-form-component="true"]'):
            if fs.find_elements(By.CSS_SELECTOR, 'input[type="radio"]:checked'):
                continue
            question = self.safe_text(fs, "legend", "Unnamed question")
            options = [self.safe_text(fs, f'label[for="{r.get_attribute("id")}"]') for r in fs.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')]
            label = f"{question} (Choose one: {', '.join([o for o in options if o])})"
            fields.append({"id": fs.get_attribute("id"), "label": label})
        return fields

    def extract_selects(self, form):
        """Extract unfilled dropdowns."""
        fields = []
        for sel in form.find_elements(By.CSS_SELECTOR, "select"):
            if not sel.is_displayed() or not sel.is_enabled():
                continue
            if (sel.get_attribute("value") or "").strip().lower() not in ["", "select an option"]:
                continue

            label = self.extract_label_text(form, sel.get_attribute("id"))
            options = [o.text.strip() for o in sel.find_elements(By.TAG_NAME, "option") if o.text.strip()]
            label_full = f"{label} (Choose from: {', '.join(options)})"
            fields.append({"id": sel.get_attribute("id"), "label": label_full})
        return fields

    def extract_label_text(self, form, field_id):
        """Safely extract visible label text."""
        try:
            label = form.find_element(By.CSS_SELECTOR, f'label[for="{field_id}"]')
            # Try span, fallback to label text itself
            spans = label.find_elements(By.CSS_SELECTOR, "span:not(.visually-hidden)")
            if spans:
                text = " ".join(s.text.strip() for s in spans if s.text.strip())
            else:
                text = label.text.strip()
        except Exception:
            # Fallback: maybe label isn't linked with 'for' attribute
            try:
                input_el = form.find_element(By.ID, field_id)
                container = input_el.find_element(By.XPATH, "./ancestor::div[contains(@class, 'artdeco-text-input')]")
                text = container.find_element(By.TAG_NAME, "label").text.strip()
            except Exception:
                return ""

        # Handle duplicated patterns like "Q?Q?"
        if len(text) % 2 == 0 and text[: len(text)//2] == text[len(text)//2:]:
            text = text[: len(text)//2]

        return text.strip()

    def safe_text(self, root, selector, default=""):
        """Safely extract text from an element."""
        try:
            return root.find_element(By.CSS_SELECTOR, selector).text.strip()
        except Exception:
            return default

    def element_exists(self, css_selector: str, text: str = None) -> bool:
        """Return True if an element exists (optionally matches text)."""
        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        if not elements:
            return False
        return any(text.lower() in el.text.lower() for el in elements) if text else True

    def click_if_exists(self, css_selector):
        """Click an element if it exists, return True if clicked."""
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, css_selector)
            el.click()
            time.sleep(settings.DELAY_TIME)
            return True
        except Exception:
            return False

    def ask_from_ai(self, payload):
        """Send unfilled questions to AI and get structured answers."""
        labels = [{"label": item["label"]} for item in payload]

        body = {
            "model": settings.DEEPINFRA_MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                            "Based on this information: ("  + settings.USER_INFORMATION + ") fill out this object: " + json.dumps(labels) +
                            "You must just return the list without any extra explanation. "
                            "If you cannot find the answer to a question based on the provided information, fill it in yourself."
                    )
                },
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        }

        try:
            response = requests.post(
                settings.DEEPINFRA_API_URL,
                headers=headers,
                json=body,
                timeout=60
            ).json()

            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return self.extract_json_array(content)

        except Exception as e:
            print(f"⚠️ AI request failed: {e}")
            return []

    def extract_json_array(self, text: str):
        """Extract and safely parse a JSON array from raw text."""
        match = re.search(r"\[.*]", text, re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            cleaned = re.sub(r"[\r\n]", "", match.group(0))
            try:
                return json.loads(cleaned)
            except Exception:
                return []

    def get_answer_by_label(self, data, label):
        """Get an answer by its label."""
        for item in data:
            if item.get("label") == label:
                return item.get("answer")
        return None
