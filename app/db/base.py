from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Base class for declarative models. Import-safe: no engine is built here.
Base = declarative_base()

# The engine and session factory are built lazily on first use. Creating the
# engine at import time bound the whole package to PostgreSQL, so importing any
# model required psycopg2 even for SQLite tests and for tooling that only needs
# the metadata.
_engine = None
_SessionLocal = None


def get_engine():
    """Return the process-wide engine, creating it on first call."""
    global _engine
    if _engine is None:
        url = settings.DATABASE_URL
        kwargs = {"pool_pre_ping": True}
        # SQLite (tests, benchmarks) does not support connection pool sizing.
        if not url.startswith("sqlite"):
            kwargs.update(pool_size=10, max_overflow=20)
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session_factory():
    """Return the process-wide sessionmaker, creating it on first call."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


def get_db():
    """Dependency for getting database session."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
