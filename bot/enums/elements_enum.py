from enum import Enum

class ElementsEnum(str, Enum):
    APPLY_BTN_ID = "jobs-apply-button-id"
    SEL_NEXT_STEP = '[aria-label="Continue to next step"]'
    SEL_REVIEW = '[aria-label="Review your application"]'
    SEL_SUBMIT = '[aria-label="Submit application"]'
    SEL_DISMISS = '[aria-label="Dismiss"]'
    SEL_DISCARD = '[data-control-name="discard_application_confirm_btn"]'
    SEL_ERROR_ICON = '[type="error-pebble-icon"]'
