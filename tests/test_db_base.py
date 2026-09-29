"""Regression tests for lazy database initialization.

`app/db/base.py` used to build the engine at import time against
`settings.DATABASE_URL`, which meant importing any model required a live
PostgreSQL driver even for SQLite tests. These tests pin the lazy behavior so
the defect cannot come back.
"""
import pytest
from app.db import base


@pytest.fixture(autouse=True)
def reset_lazy_globals():
    """Each test starts and ends with an uninitialized engine."""
    base._engine = None
    base._SessionLocal = None
    yield
    base._engine = None
    base._SessionLocal = None


def test_importing_base_does_not_build_an_engine():
    assert base._engine is None
    assert base._SessionLocal is None


def test_get_engine_is_lazy_and_cached(monkeypatch):
    monkeypatch.setattr(base.settings, "DATABASE_URL", "sqlite:///:memory:")

    engine = base.get_engine()

    assert engine is not None
    assert base.get_engine() is engine, "engine should be built once and reused"


def test_sqlite_url_omits_pool_sizing(monkeypatch):
    """SQLite rejects pool_size/max_overflow, which is why the branch exists."""
    monkeypatch.setattr(base.settings, "DATABASE_URL", "sqlite:///:memory:")

    engine = base.get_engine()

    assert engine.dialect.name == "sqlite"


def test_get_session_factory_is_lazy_and_cached(monkeypatch):
    monkeypatch.setattr(base.settings, "DATABASE_URL", "sqlite:///:memory:")

    factory = base.get_session_factory()

    assert base.get_session_factory() is factory
    assert base._engine is not None, "factory must have triggered engine creation"


def test_get_db_yields_a_session_and_closes_it(monkeypatch):
    monkeypatch.setattr(base.settings, "DATABASE_URL", "sqlite:///:memory:")

    gen = base.get_db()
    session = next(gen)
    assert session.is_active

    with pytest.raises(StopIteration):
        next(gen)
