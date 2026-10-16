from fastapi import APIRouter

from ..schemas.user_input import RecommendationRequest, RecommendationResponse
from ..services.recommender import recommender

router = APIRouter(tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def post_recommendations(payload: RecommendationRequest) -> RecommendationResponse:
    """Rank rule-based nutrition recommendations for one day of features against user targets."""
    recs = recommender.generate_recommendations(
        daily_features=payload.daily_features.model_dump(exclude_none=True),
        user_targets=payload.user_targets.model_dump(exclude_none=True),
    )
    return RecommendationResponse(recommendations=recs)
