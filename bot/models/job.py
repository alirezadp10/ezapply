from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from bot.models import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(20))
    title = Column(String(50))
    description = Column(Text)
    country = Column(String(50))
    keyword = Column(String(50))
    url = Column(String(50))
    status = Column(String(10), nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
