from enum import Enum

class JobStatusEnum(str, Enum):
    FAILED = "failed"
    CANCELED = "canceled"
    READY_FOR_APPLY = "ready_for_apply"
    SUCCEEDED = "succeeded"

    def __str__(self) -> str:
        return self.value