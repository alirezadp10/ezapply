from enum import Enum

class JobReasonEnum(str, Enum):
    APPLY_BUTTON = "Couldn't find apply button"
    FILL_OUT_FORM = "Couldn't fill out the form"
    WORK_TYPE_MISMATCH = "Work type mismatch"

    def __str__(self) -> str:
        return self.value