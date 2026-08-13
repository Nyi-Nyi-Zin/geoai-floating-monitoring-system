from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine
from app.schemas.health import DatabaseHealth, HealthResponse


def get_health() -> HealthResponse:
    if engine is None:
        database = DatabaseHealth(
            status="not_configured",
            detail="Set DATABASE_URL to enable database-backed endpoints.",
        )
        status = "healthy"
    else:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            database = DatabaseHealth(status="healthy")
            status = "healthy"
        except SQLAlchemyError:
            database = DatabaseHealth(
                status="unhealthy",
                detail="Database connection failed; verify DATABASE_URL and PostgreSQL.",
            )
            status = "degraded"

    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=database,
    )
