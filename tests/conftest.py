import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app import models  # noqa: F401 — registers models on Base.metadata


@pytest.fixture
def db_session():
    """Fresh in-memory SQLite DB per test. Good enough for model/service
    logic — nothing here depends on Postgres-specific behavior."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
