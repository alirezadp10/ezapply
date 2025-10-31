from enum import Enum

class ModesEnum(str, Enum):
    EXPLORE = "explore"
    FAKE = "fake"
    REAL = "real"
    TEST = "test"

    def __str__(self) -> str:
        return self.value
