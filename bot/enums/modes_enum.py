from enum import Enum


class ModesEnum(str, Enum):
    EXPLORE = "explore"
    FETCH_QUESTIONS = "fetch questions"
    SCORE = "score"
    APPLY = "apply"

    def __str__(self) -> str:
        return self.value
