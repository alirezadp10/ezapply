from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from bot.config import settings
from bot.models import Job, Base, Field
from sqlalchemy.exc import IntegrityError
import numpy as np


class DBManager:
    def __init__(self):
        self.engine = create_engine(settings.SQLITE_DB_PATH, echo=False)
        self.session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def save_job(
        self, job_id: str, title: str, description: str, country: str, keyword: str, url: str
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

    def save_field(
        self, label: str, value: str, type: str, embeddings: list, job_id: str
    ):
        session = self.session()
        try:
            field = session.execute(
                select(Field).where(Field.label == label)
            ).scalar_one_or_none()

            if field:
                field.value = value
                field.type = type
            else:
                arr = np.array(embeddings, dtype=np.float32)
                field = Field(
                    label=label,
                    value=value,
                    type=type,
                    embedding=arr.tobytes(),
                    job_id=job_id,
                )
                session.add(field)

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
