from sqlalchemy import Column, Integer, String, DateTime, LargeBinary
from datetime import datetime
from bot.models import Base


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(255))
    value = Column(String(255))
    type = Column(String(20))
    job_id = Column(String(20))
    embedding = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)