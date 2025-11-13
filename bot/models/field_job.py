from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, UniqueConstraint

from bot.models import Base


class FieldJob(Base):
    __tablename__ = "field_jobs"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer())
    job_id = Column(Integer())
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("job_id", "field_id", name="uix_fieldjob_job_field"),
    )