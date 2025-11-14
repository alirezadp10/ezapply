from sqlalchemy import select

from bot.models import FieldJob


class FieldJobRepository:
    def exists(self, session, job_id, field_id):
        return (
            session.execute(
                select(FieldJob).where(FieldJob.job_id == job_id, FieldJob.field_id == field_id)
            ).scalar_one_or_none()
            is not None
        )

    def insert(self, session, job_id, field_id):
        fj = FieldJob(job_id=job_id, field_id=field_id)
        session.add(fj)
        return fj
