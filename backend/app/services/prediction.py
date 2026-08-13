from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class PredictionResult:
    """Auditable output contract for a future, externally implemented model."""

    geo_asset_id: UUID
    risk_score: float
    confidence: float
    model_version: str
    contributing_factors: list[dict[str, Any]]
    explanation: str
    review_status: str = "pending"
    override_reason: str | None = None


class RiskPredictionService(Protocol):
    """Boundary that keeps ML inference out of API and persistence code.

    Implementations must surface confidence and explanations. Real-world action
    should remain pending until an authorized human review workflow accepts it.
    """

    def predict(
        self,
        geo_asset_id: UUID,
        *,
        layer_ids: list[UUID],
        observation_ids: list[UUID],
    ) -> PredictionResult:
        ...
