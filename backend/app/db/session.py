from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = (
    create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )
    if settings.database_url
    else None
)

SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    if engine is not None
    else None
)
