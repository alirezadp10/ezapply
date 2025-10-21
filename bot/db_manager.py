from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from bot.models import Job, Base, Field
from sqlalchemy.exc import IntegrityError


class DBManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def save_job(self, title: str, job_id: int, status: str, url: str, reason: Optional[str] = None):
        session = self.Session()
        job = Job(title=title, job_id=job_id, status=status, url=url, reason=reason)
        session.add(job)
        session.commit()
        session.close()

    def save_field(self, label: str, value: str, tag: str, job_id: int):
        session = self.Session()
        try:
            field = session.execute(
                select(Field).where(Field.label == label)
            ).scalar_one_or_none()

            if field:
                field.value = value
                field.tag = tag
            else:
                field = Field(label=label, value=value, tag=tag, job_id=job_id)
                session.add(field)

            session.commit()
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()

    def is_applied_for_job(self, job_id: int) -> bool:
        session = self.Session()
        job = session.query(Job).filter_by(job_id=job_id).first()
        session.close()
        if job:
            return True
        return False