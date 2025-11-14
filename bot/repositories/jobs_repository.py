from sqlalchemy import or_, select, update

from bot.enums import JobStatusEnum
from bot.models import Job


class JobsRepository:
    def exists(self, session, job_id: str) -> bool:
        return session.execute(select(Job).where(Job.job_id == job_id)).scalar_one_or_none() is not None

    def insert(self, session, **data) -> Job:
        job = Job(**data)
        session.add(job)
        return job

    def get_by_id(self, session, *, job_id=None, pk=None):
        q = session.query(Job)
        if job_id:
            return q.filter(Job.job_id == job_id).first()
        return q.filter(Job.id == pk).first()

    def get_not_applied(self, session):
        return (
            session.query(Job)
            .filter(
                or_(
                    Job.status == JobStatusEnum.FILL_OUT_FORM,
                    Job.status == JobStatusEnum.APPLY_BUTTON,
                    Job.status.is_(None),
                )
            )
            .all()
        )

    def update_status(self, session, pk, status):
        session.execute(update(Job).where(Job.id == pk).values(status=status))
