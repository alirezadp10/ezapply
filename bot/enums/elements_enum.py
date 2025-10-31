from enum import Enum


class ElementsEnum(str, Enum):
    APPLY_BTN_ID = 'jobs-apply-button-id'
    JOB_TITLE = '.job-card-list__title--link span[aria-hidden="true"]'
    JOB_ID = 'div[data-job-id]'
    SEL_NEXT_STEP = '[aria-label="Continue to next step"]'
    SEL_REVIEW = '[aria-label="Review your application"]'
    SEL_SUBMIT = '[aria-label="Submit application"]'
    SEL_DISMISS = '[aria-label="Dismiss"]'
    SEL_DISCARD = '[data-control-name="discard_application_confirm_btn"]'
    SEL_ERROR_ICON = '[type="error-pebble-icon"]'
    SEL_MODAL = "[data-test-modal]"
    SEL_CONTENTEDITABLE = '[contenteditable="true"]'
    SEL_INPUT_RADIO = 'input[type="radio"]'
    SEL_INPUT_CHECKBOX = 'input[type="checkbox"]'
    TAG_LABEL = "label"
    TAG_FORM = "form"
    TAG_OPTION = "option"
    TAG_SPAN = "span"
    TAG_LEGEND = "legend"
    SEL_INPUT_NOT_RADIO = 'input:not([type="radio"])'
    SEL_SELECT = "select"
    SEL_TEXTAREA = "textarea"
    SEL_FIELDSET = "fieldset"
    SEL_LABEL_FOR_TPL = "label[for='{id}']"
    ATTR_ROLE_COMBOBOX = "combobox"
    SEL_FIELDSET_CHECKBOX_COMPONENT = (
        'fieldset[data-test-checkbox-form-component="true"]'
    )

    def __str__(self) -> str:
        return self.value