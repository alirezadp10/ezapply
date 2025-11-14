import numpy as np
from sqlalchemy import select

from bot.models import Field


class FieldsRepository:
    def exists(self, session, label, value):
        return session.execute(select(Field).where(Field.label == label, Field.value == value)).scalar_one_or_none()

    def insert(self, session, label, value, type, embeddings):
        field = Field(
            label=label,
            value=value,
            type=type,
            embedding=np.array(embeddings, dtype=np.float32).tobytes(),
        )
        session.add(field)
        return field

    def get_all(self, session):
        return session.query(Field).all()

    def get_by_label(self, session, label):
        return session.execute(select(Field).where(Field.label == label)).scalar_one_or_none()
