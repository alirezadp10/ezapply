from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from bot.settings import settings

# ---------------------------------------------------------
# Engine + Session factory
# ---------------------------------------------------------

engine = create_engine(
    settings.SQLITE_DB_PATH,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=Session,
)


# ---------------------------------------------------------
# Context-managed session
# ---------------------------------------------------------


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Provides a transactional scope around a series of operations.
    Automatically commits on success and rolls back on failure.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
