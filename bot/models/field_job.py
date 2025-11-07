from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

from bot.models import Base


class FieldJob(Base):
    __tablename__ = "field_jobs"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer())
    job_id = Column(Integer())
    created_at = Column(DateTime, default=datetime.utcnow)
