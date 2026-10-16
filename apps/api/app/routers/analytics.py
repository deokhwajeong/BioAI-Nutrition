"""Trend analytics over logged days."""

from fastapi import APIRouter

from ..schemas.analytics import TrendsRequest, TrendsResponse
from ..services.analytics import SAMPLE_TARGETS, compute_trends, synthetic_days

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/trends", response_model=TrendsResponse)
def post_trends(req: TrendsRequest) -> TrendsResponse:
    """Rolling means, weekly slopes, goal adherence, and rule hits for the days sent."""
    days = [d.model_dump(exclude_none=True) for d in req.days]
    return TrendsResponse(**compute_trends(days, req.user_targets.model_dump(exclude_none=True)))


@router.get("/sample", response_model=TrendsResponse)
def sample_trends() -> TrendsResponse:
    """Trends for 28 days of a fictional user (fixed seed, identical on every call)."""
    return TrendsResponse(
        **compute_trends(synthetic_days(), SAMPLE_TARGETS),
        synthetic=True,
        note="Synthetic sample user, 28 generated days. Descriptive statistics only.",
    )
