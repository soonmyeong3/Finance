"""Creates all tables."""

from app.core.db import Base, engine
from app import models  # noqa: F401 — imported for side effect of model registration

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("tables created")
