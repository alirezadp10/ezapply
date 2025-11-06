from __future__ import annotations

import numpy as np
from contextlib import contextmanager
from typing import Iterator, Optional, List, cast

from sqlalchemy import create_engine, or_, update, delete
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from loguru import logger

from bot.config import settings
from bot.enums import JobStatusEnum
from bot.models import Base, Job, Field


class DBManager:
    """Centralized database manager for Jobs and Fields."""

    def __init__(self):
        self.engine = create_engine(settings.SQLITE_DB_PATH, echo=False, future=True)
        self.SessionLocal = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=Session
        )
        Base.metadata.create_all(self.engine)

    # ----------------------------------------------------- #
    # Context manager
    # ----------------------------------------------------- #
    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """Provide a transactional scope for a DB session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ----------------------------------------------------- #
    # Helpers
    # ----------------------------------------------------- #
    def _commit(self, session: Session) -> bool:
        """Safely commit a transaction."""
        try:
            session.commit()
            return True
        except IntegrityError as e:
            logger.warning(f"IntegrityError: {e}")
            session.rollback()
            return False
        except Exception as e:
            logger.exception(f"Unexpected DB error: {e}")
            session.rollback()
            return False

    # ----------------------------------------------------- #
    # Job operations
    # ----------------------------------------------------- #
    def save_job(
        self,
        job_id: str,
        title: str,
        description: str,
        country: str,
        keyword: str,
        url: str,
    ) -> bool:
        """Insert a new job record."""
        with self.SessionLocal() as session:
            job = Job(
                job_id=job_id,
                title=title,
                description=description,
                country=country,
                keyword=keyword,
                url=url,
            )
            session.add(job)
            return self._commit(session)

    def get_not_applied_jobs(self) -> list[Job]:
        """Return jobs not yet applied and not canceled."""
        with self.SessionLocal() as session:
            jobs = (
                session.query(Job)
                .filter(
                    Job.applied_at.is_(None),
                    or_(Job.status.is_(None), Job.status != JobStatusEnum.CANCELED, Job.status != JobStatusEnum.READY_FOR_APPLY),
                )
                .all()
            )
            return cast(list[Job], jobs)

    def get_job_by_id(
        self, job_id: Optional[str] = None, pk: Optional[int] = None
    ) -> Optional[Job]:
        """Fetch a single job by its primary key or LinkedIn job_id."""
        if not job_id and not pk:
            raise ValueError("You must provide either job_id or pk")
        with self.SessionLocal() as session:
            query = session.query(Job)
            if job_id:
                return query.filter(Job.job_id == job_id).first()
            return query.filter(Job.id == pk).first()

    def get_jobs_by_status(self, status: JobStatusEnum) -> List[Job]:
        """Return all jobs matching a specific status."""
        with self.SessionLocal() as session:
            return session.query(Job).filter(Job.status == status).all()

    def update_job_status(
        self, pk: int, status: JobStatusEnum, reason: Optional[str] = None
    ) -> bool:
        """Update a job's status and optional reason."""
        with self.SessionLocal() as session:
            stmt = update(Job).where(Job.id == pk).values(status=status, reason=reason)
            session.execute(stmt)
            return self._commit(session)

    def cancel_job(self, pk: int, reason: str) -> bool:
        """Mark a job as canceled."""
        return self.update_job_status(pk, JobStatusEnum.CANCELED, reason)

    def delete_job(self, pk: int, soft: bool = True) -> bool:
        """
        Delete a job record.
        If soft=True, mark as deleted. Otherwise, remove permanently.
        """
        with self.SessionLocal() as session:
            if soft:
                stmt = (
                    update(Job).where(Job.id == pk).values(status=JobStatusEnum.DELETED)
                )
                session.execute(stmt)
            else:
                stmt = delete(Job).where(Job.id == pk)
                session.execute(stmt)
            return self._commit(session)

    def is_applied_for_job(self, job_id: str) -> bool:
        """Check if a job has been applied for (not failed)."""
        with self.SessionLocal() as session:
            job = (
                session.query(Job)
                .filter(Job.job_id == job_id, Job.status != JobStatusEnum.FAILED)
                .first()
            )
            return job is not None

    # ----------------------------------------------------- #
    # Field operations
    # ----------------------------------------------------- #
    def save_field(
        self,
        label: str,
        value: str,
        type: str,
        embeddings: list[float],
        job_id: str,
    ) -> bool:
        """Save a new field and its embedding."""
        with self.SessionLocal() as session:
            field = Field(
                label=label,
                value=value,
                type=type,
                embedding=np.array(embeddings, dtype=np.float32).tobytes(),
                job_id=job_id,
            )
            session.add(field)
            return self._commit(session)

    def get_all_fields(self) -> List[Field]:
        """Return all field records."""
        with self.SessionLocal() as session:
            return session.query(Field).all()

    def get_field_embeddings(self, job_id: Optional[str] = None) -> List[np.ndarray]:
        """Return decoded embeddings for all fields (or specific job)."""
        with self.SessionLocal() as session:
            query = session.query(Field)
            if job_id:
                query = query.filter(Field.job_id == job_id)
            fields = query.all()
            return [
                np.frombuffer(f.embedding, dtype=np.float32)
                for f in fields
                if f.embedding
            ]
