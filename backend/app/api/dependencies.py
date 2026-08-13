from collections.abc import Generator
from typing import Any, cast

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


class _UnconfiguredSession:
    """Delay the configuration error until after request body validation."""

    def __getattr__(self, _name: str) -> Any:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "database_not_configured",
                "message": "DATABASE_URL is required for GeoAsset operations.",
            },
        )


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        yield cast(Session, _UnconfiguredSession())
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
