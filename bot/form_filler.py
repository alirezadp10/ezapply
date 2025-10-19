from loguru import logger
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By

class FormFiller:
    def __init__(self, driver):
        self.driver = driver

    def fill_fields(self, fields, answers):
        for item in fields:
            answer = next((a["answer"] for a in answers if a["label"] == item["label"]), None)
            if not answer:
                continue
            try:
                el = self.driver.find_element(By.ID ,item["id"])
                if el.tag_name == "input":
                    el.clear()
                    el.send_keys(answer)
                elif el.tag_name == "select":
                    Select(el).select_by_visible_text(answer)
            except Exception as e:
                logger.warning(f"⚠️ Could not fill {item['label']}: {e}")
