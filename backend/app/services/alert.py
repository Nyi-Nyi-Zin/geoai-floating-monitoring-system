import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.schemas.alert import (
    AlertAcknowledge,
    AlertCollection,
    AlertResponse,
)
from app.schemas.geo_asset import PaginationMeta


def _not_found(alert_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "alert_not_found",
            "message": f"Alert '{alert_id}' was not found.",
        },
    )


def _to_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        station_id=alert.station_id,
        observation_id=alert.observation_id,
        risk_level=alert.risk_level,
        water_level_cm=alert.water_level_cm,
        threshold_cm=alert.threshold_cm,
        message=alert.message,
        status=alert.status,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        acknowledgement_notes=alert.acknowledgement_notes,
        created_at=alert.created_at,
    )


class AlertService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        page: int,
        page_size: int,
        alert_status: str | None,
        risk_level: str | None,
        station_id: str | None,
    ) -> AlertCollection:
        query = select(Alert)
        count_query = select(func.count()).select_from(Alert)
        filters = []
        if alert_status:
            filters.append(Alert.status == alert_status)
        if risk_level:
            filters.append(Alert.risk_level == risk_level)
        if station_id:
            filters.append(Alert.station_id == station_id)
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)
        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return AlertCollection(
            items=[_to_response(row) for row in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
        )

    def acknowledge(
        self,
        alert_id: UUID,
        payload: AlertAcknowledge,
    ) -> AlertResponse:
        alert = self.db.get(Alert, alert_id)
        if alert is None:
            raise _not_found(alert_id)
        if alert.status == "acknowledged":
            return _to_response(alert)
        alert.status = "acknowledged"
        alert.acknowledged_by = payload.acknowledged_by
        alert.acknowledged_at = datetime.now(UTC)
        alert.acknowledgement_notes = payload.notes
        self.db.commit()
        self.db.refresh(alert)
        return _to_response(alert)
