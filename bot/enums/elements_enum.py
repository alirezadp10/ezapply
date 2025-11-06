from enum import Enum


class ElementsEnum(str, Enum):
    apply_button_id = "jobs-apply-button-id"
    job_title = '.job-card-list__title--link span[aria-hidden="true"]'
    job_id = "div[data-job-id]"
    next_step_button = '[aria-label="Continue to next step"]'
    review_button = '[aria-label="Review your application"]'
    submit_button = '[aria-label="Submit application"]'
    dismiss_button = '[aria-label="Dismiss"]'
    discard_button = '[data-control-name="discard_application_confirm_btn"]'
    error_icon = '[type="error-pebble-icon"]'
    modal = "[data-test-modal]"
    contenteditable = '[contenteditable="true"]'
    input_radio = 'input[type="radio"]'
    input_checkbox = 'input[type="checkbox"]'
    label = "label"
    form = "form"
    option = "option"
    span = "span"
    legend = "legend"
    input_not_radio = 'input:not([type="radio"])'
    select = "select"
    textarea = "textarea"
    fieldset = "fieldset"
    label_for_template = "label[for='{id}']"
    role_combobox = "combobox"
    job_items = "jobs-search__results-list"
    sign_in_modal = "#base-contextual-sign-in-modal > div > section > button"
    offsite_apply_icon = '[data-svg-class-name="apply-button__offsite-apply-icon-svg"]'
    checkbox_fieldset_component = 'fieldset[data-test-checkbox-form-component="true"]'
    job_card_active = "job-search-card--active"
    job_description = "description__text"

    def __str__(self) -> str:
        return self.value
