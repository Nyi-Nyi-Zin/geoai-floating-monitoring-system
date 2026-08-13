from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.flood_intelligence import (
    ExposureSummary,
    FloodIntelligenceSummary,
    SarValidationReport,
)
from app.services.flood_intelligence import FloodIntelligenceService

router = APIRouter(prefix="/flood-intelligence", tags=["flood-intelligence"])


@router.get(
    "/summary",
    response_model=FloodIntelligenceSummary,
    summary="Combined flood intelligence: ML, SAR, exposure, and early warning",
)
def intelligence_summary(
    event_id: str | None = None,
    use_forecast: bool = False,
    db: Session = Depends(get_db),
) -> FloodIntelligenceSummary:
    return FloodIntelligenceService(db).intelligence_summary(
        event_id=event_id,
        use_forecast=use_forecast,
    )


@router.get(
    "/sar-validation",
    response_model=SarValidationReport,
    summary="ML vs SAR validation metrics (independent Sentinel-1 labels)",
)
def sar_validation(db: Session = Depends(get_db)) -> SarValidationReport:
    return FloodIntelligenceService(db).sar_validation_report()


@router.get(
    "/exposure",
    response_model=ExposureSummary,
    summary="Building and area exposure for flagged flood-risk cells",
)
def exposure_summary(
    use_forecast: bool = False,
    db: Session = Depends(get_db),
) -> ExposureSummary:
    return FloodIntelligenceService(db).exposure_summary(
        use_forecast=use_forecast,
    )
