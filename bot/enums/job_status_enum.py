from enum import Enum


class JobStatusEnum(str, Enum):
    APPLY_BUTTON = "apply_button"
    FILL_OUT_FORM = "fill_out_form"
    WORK_TYPE_MISMATCH = "work_type_mismatch"
    EXPIRED = "expired"
    READY_FOR_APPLY = "ready_for_apply"
    APPLIED = "applied"

    @property
    def message(self) -> str:
        return {
            self.APPLY_BUTTON: "Couldn't find apply button",
            self.FILL_OUT_FORM: "Couldn't fill out the form",
            self.WORK_TYPE_MISMATCH: "Work type mismatch",
            self.EXPIRED: "Request has been expired",
            self.READY_FOR_APPLY: "Ready for apply",
            self.APPLIED: "applied",
        }[self]

    def __str__(self) -> str:
        return self.value
