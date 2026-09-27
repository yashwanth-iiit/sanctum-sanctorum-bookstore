"""Additional checks reuse the starter fixtures without modifying tests/."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from tests.conftest import client, clock, make_book, make_member

__all__ = ["client", "clock", "make_book", "make_member", "db"]


@pytest.fixture
def db(tmp_path):
    """A real SQLite file allows an independent session to inspect committed data."""
    engine = create_engine(f"sqlite:///{tmp_path / 'integrity.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        yield session
    engine.dispose()
