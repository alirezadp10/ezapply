from enum import Enum


class ElementsEnum(str, Enum):
    JOB_TITLE = '.job-card-list__title--link span[aria-hidden="true"]'
    JOB_ID = "div[data-job-id]"
    NEXT_STEP_BUTTON = '[aria-label="Continue to next step"]'
    REVIEW_BUTTON = '[aria-label="Review your application"]'
    SUBMIT_BUTTON = '[aria-label="Submit application"]'
    DISMISS_BUTTON = '[aria-label="Dismiss"]'
    DISCARD_BUTTON = '[data-control-name="discard_application_confirm_btn"]'
    ERROR_ICON = '[type="error-pebble-icon"]'
    MODAL = "[data-test-modal]"
    CONTENTEDITABLE = '[contenteditable="true"]'
    INPUT_RADIO = 'input[type="radio"]'
    INPUT_CHECKBOX = 'input[type="checkbox"]'
    LABEL = "label"
    FORM = "form"
    OPTION = "option"
    SPAN = "span"
    LEGEND = "legend"
    INPUT_NOT_RADIO = 'input:not([type="radio"])'
    SELECT = "select"
    TEXTAREA = "textarea"
    FIELDSET = "fieldset"
    LABEL_FOR_TEMPLATE = "label[for='{id}']"
    ROLE_COMBOBOX = "combobox"
    JOB_ITEMS = "jobs-search__results-list"
    SIGN_IN_MODAL = "#base-contextual-sign-in-modal > div > section > button"
    OFFSITE_APPLY_ICON = '[data-svg-class-name="apply-button__offsite-apply-icon-svg"]'
    CHECKBOX_FIELDSET_COMPONENT = 'fieldset[data-test-checkbox-form-component="true"]'
    JOB_CARD_ACTIVE = "job-search-card--active"
    JOB_DESCRIPTION = "description__text"

    def __str__(self) -> str:
        return self.value
