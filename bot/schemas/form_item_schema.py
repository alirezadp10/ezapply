from typing import Dict
from dataclasses import dataclass


@dataclass
class FormItemSchema:
    label: str
    answer: str = ""
    type: str = ""
    embeddings: bytes = b""  # float32 bytes

    @staticmethod
    def from_payload_entry(entry: Dict[str, str]) -> "FormItemSchema":
        return FormItemSchema(label=entry["label"])
