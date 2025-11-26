from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_engine(settings.assembled_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db() -> Session:
    """Provide a scoped database session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
def lifespan_context():
    """Manage application startup and shutdown activities."""

    logger.info("Opening database engine")
    try:
        # Initialize engine by connecting once.
        with engine.connect():
            logger.info("Database connection established")
        yield
    finally:
        logger.info("Disposing database engine")
        engine.dispose()
