from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from bot.models import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(20))
    title = Column(String(50))
    description = Column(Text)
    alignment = Column(Integer, nullable=True)
    status = Column(String(10), nullable=True)
    reason = Column(String(255), nullable=True)
    url = Column(String(50))
    applied_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
