from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from bot.models import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50))
    job_id = Column(String(20))
    status = Column(String(10))
    reason = Column(String(255), nullable=True)
    url = Column(String(50))
    applied_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)