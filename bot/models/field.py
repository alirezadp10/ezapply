from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from bot.models import Base


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(255))
    value = Column(String(255))
    tag = Column(String(20))
    job_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)