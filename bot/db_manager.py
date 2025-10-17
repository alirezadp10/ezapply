from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bot.models import Job, Base
from loguru import logger

class DBManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        logger.info("✅ Database initialized.")

    def save_job(self, job_id: int, status: str, url: str):
        session = self.Session()
        job = Job(job_id=job_id, status=status, url=url)
        session.add(job)
        session.commit()
        session.close()
        logger.info(f"💾 Saved job: {job_id}")

    def is_applied_for_job(self, job_id: int) -> bool:
        session = self.Session()
        job = session.query(Job).filter_by(job_id=job_id).first()
        session.close()
        if job:
            logger.info("Already applied to this job.")
            return True
        logger.info("No previous application found.")
        return False