from enum import Enum

class JobStatusEnum(str, Enum):
    FAILED = "failed"
    CANCELED = "canceled"
    SUCCEEDED = "succeeded"

    def __str__(self) -> str:
        return self.value