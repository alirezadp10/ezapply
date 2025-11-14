from selenium.webdriver.common.by import By

from bot.enums import ElementsEnum


def has_exhausted_limit(driver) -> bool:
    xpath = (
        "//*[text()=\"You’ve reached today's Easy Apply limit. "
        "Great effort applying today. We limit daily submissions "
        'to help ensure each application gets the right attention."]'
    )
    return bool(driver.find_elements(By.XPATH, xpath))

def has_offsite_apply_icon(driver) -> bool:
    return bool(driver.find_elements(By.CSS_SELECTOR, ElementsEnum.OFFSITE_APPLY_ICON))

def body_has_text(driver, text: str) -> bool:
    body = driver.find_element(By.TAG_NAME, "body")
    return text in body.text

def navigated_to_single_page(driver) -> bool:
    return body_has_text(driver, "People also viewed")
