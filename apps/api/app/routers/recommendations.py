from fastapi import APIRouter

from ..schemas.user_input import RecommendationRequest, RecommendationResponse
from ..services.recommendations import generate_recommendations

router = APIRouter(tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def post_recommendations(payload: RecommendationRequest) -> RecommendationResponse:
    """Evaluate the YAML rules in rules/ against one day of features and the user's targets.

    Every matching rule is returned, highest priority first. An empty list means no rule
    fired. Suggestions are general wellness guidance, not medical advice.
    """
    recs = generate_recommendations(
        daily_features=payload.daily_features.model_dump(exclude_none=True),
        user_targets=payload.user_targets.model_dump(exclude_none=True),
        top_n=payload.top_n,
    )
    return RecommendationResponse(recommendations=recs)
