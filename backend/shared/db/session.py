from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shared.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,# 10 connetions
    max_overflow=20,#if needed 20 
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Generator-style session for FastAPI Depends.

    Worker / MCP can use SessionLocal() directly with a context manager.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()