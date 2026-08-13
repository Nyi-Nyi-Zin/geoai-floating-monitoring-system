from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.alert import (
    AlertAcknowledge,
    AlertCollection,
    AlertResponse,
    AlertStatus,
    RiskLevel,
)
from app.services.alert import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])

Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=500)]


@router.get(
    "",
    response_model=AlertCollection,
    summary="List deterministic water-level threshold alerts",
)
def list_alerts(
    page: Page = 1,
    page_size: PageSize = 100,
    alert_status: AlertStatus | None = Query(default=None, alias="status"),
    risk_level: RiskLevel | None = None,
    station_id: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> AlertCollection:
    return AlertService(db).list(
        page=page,
        page_size=page_size,
        alert_status=alert_status,
        risk_level=risk_level,
        station_id=station_id,
    )


@router.patch(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an alert without deleting its audit record",
)
def acknowledge_alert(
    alert_id: UUID,
    payload: AlertAcknowledge,
    db: Session = Depends(get_db),
) -> AlertResponse:
    return AlertService(db).acknowledge(alert_id, payload)
