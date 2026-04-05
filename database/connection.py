from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path

from config.settings import settings
from database.models import Base

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.db_url
        if db_url.startswith("sqlite"):
            db_path = db_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            db_url,
            echo=(settings.log_level == "DEBUG"),
            pool_pre_ping=True,
        )
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
