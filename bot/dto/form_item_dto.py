from typing import Dict
from dataclasses import dataclass


@dataclass
class FormItemDTO:
    label: str
    answer: str = ""
    type: str = ""
    embeddings: bytes = b""  # float32 bytes

    @staticmethod
    def from_payload_entry(entry: Dict[str, str]) -> "FormItemDTO":
        return FormItemDTO(label=entry["label"])
