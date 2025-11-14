from pydantic import BaseModel


class FormLabelSchema(BaseModel):
    label: str
    answer: str
