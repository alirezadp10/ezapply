from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By


class FormFiller:
    def __init__(self, driver):
        self.driver = driver

    def fill_fields(self, fields, answers) -> list:
        result = []
        for item in fields:
            el = self.driver.find_element(By.ID, item["id"])
            answer = next(
                (a["answer"] for a in answers if a["label"] == item["label"]), None
            )

            result.append({"label": item["label"], "value": answer, "tag": el.tag_name})

            if not answer:
                continue

            if el.tag_name == "input":
                el.clear()
                el.send_keys(answer)
            elif el.tag_name == "select":
                Select(el).select_by_visible_text(answer)

        return result
