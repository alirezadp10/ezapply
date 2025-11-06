from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from bot.config import settings
from bot.enums import JobStatusEnum
from bot.models import Job, Base, Field
from sqlalchemy.exc import IntegrityError
import numpy as np


class DBManager:
    def __init__(self):
        self.engine = create_engine(settings.SQLITE_DB_PATH, echo=False)
        self.session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def save_job(
        self,
        job_id: str,
        title: str,
        description: str,
        country: str,
        keyword: str,
        url: str,
    ):
        session = self.session()
        job = Job(
            job_id=job_id,
            title=title,
            description=description,
            country=country,
            keyword=keyword,
            url=url,
        )
        session.add(job)
        session.commit()
        session.close()

    def get_not_applied_jobs(self):
        session = self.session()
        jobs = (
            session.query(Job)
            .filter(
                Job.applied_at.is_(None),
                or_(Job.status.is_(None), Job.status != JobStatusEnum.CANCELED),
            )
            .all()
        )
        session.close()
        return jobs

    def cancel_job(self, pk: int, reason: str):
        session = self.session()
        session.query(Job).filter(Job.id == pk).update(
            {"reason": reason, "status": JobStatusEnum.CANCELED}
        )
        session.commit()
        session.close()

    def save_field(
        self, label: str, value: str, type: str, embeddings: list, job_id: str
    ):
        session = self.session()
        try:
            session.add(
                Field(
                    label=label,
                    value=value,
                    type=type,
                    embedding=np.array(embeddings, dtype=np.float32).tobytes(),
                    job_id=job_id,
                )
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()

    def is_applied_for_job(self, job_id: str) -> bool:
        session = self.session()
        job = (
            session.query(Job)
            .filter(Job.job_id == job_id, Job.status != "failed")
            .first()
        )
        session.close()
        if job:
            return True
        return False

    def get_all_fields(self) -> list:
        session = self.session()
        fields = session.query(Field).all()
        session.close()
        return fields
