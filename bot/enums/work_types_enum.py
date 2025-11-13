from enum import Enum


class WorkTypesEnum(str, Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"

    def __str__(self) -> str:
        return self.value