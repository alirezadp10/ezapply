import importlib
import inspect
import pkgutil
import re
from contextlib import contextmanager
from typing import Any, Dict, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from bot.models import Base
from bot.settings import settings

engine = create_engine(settings.SQLITE_DB_PATH, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
Base.metadata.create_all(engine)


# ----------------------------------------------------------
# Auto-commit proxy
# ----------------------------------------------------------
class RepoProxy:
    def __init__(self, manager: "DBManager", repo: Any):
        self.manager = manager
        self.repo = repo

    def __getattr__(self, item: str):
        attr = getattr(self.repo, item)

        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            result = attr(self.manager.session, *args, **kwargs)

            # auto-commit only when not in a transaction
            if not self.manager._in_transaction:
                try:
                    self.manager.session.commit()
                except Exception:
                    self.manager.session.rollback()
                    raise

            return result

        return wrapper


# ----------------------------------------------------------
# DBManager with dynamic repo discovery
# ----------------------------------------------------------
class DBManager:
    def __init__(self):
        self.session: Session = SessionLocal()
        self._in_transaction = False
        self._repos: Dict[str, Any] = {}
        self._load_repositories()

    # Dynamically import all repositories
    def _load_repositories(self):
        import bot.repositories as repo_pkg

        package_path = repo_pkg.__path__

        for module_finder, name, ispkg in pkgutil.walk_packages(package_path, repo_pkg.__name__ + "."):
            # import each module found
            module = importlib.import_module(name)

            # find repository classes inside that module
            for cls_name, cls_obj in inspect.getmembers(module, inspect.isclass):
                if cls_name.endswith("Repository"):
                    name_without_suffix = cls_name.replace("Repository", "")
                    key = re.sub(r"(?<!^)(?=[A-Z])", "_", name_without_suffix).lower()
                    instance = cls_obj()
                    self._repos[key] = RepoProxy(self, instance)

    # Access repos like db.job, db.field, db.field_jobs
    def __getattr__(self, item):
        if item in self._repos:
            return self._repos[item]
        raise AttributeError(f"'DBManager' has no repo '{item}'")

    # ------------------------------
    # Transaction
    # ------------------------------
    @contextmanager
    def transaction(self) -> Iterator["DBManager"]:
        self._in_transaction = True
        try:
            yield self
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        finally:
            self._in_transaction = False

    def close(self):
        self.session.close()
