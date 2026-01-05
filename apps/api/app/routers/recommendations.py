from fastapi import APIRouter
from ..schemas.user_input import RecommendationRequest, RecommendationResponse
from ..services.recommender import generate_recommendations


router = APIRouter(prefix="", tags=["recommendations"])

@router.post("/recommendations", response_model=RecommendationResponse)
def post_recommendations(payload: RecommendationRequest):
    recs = generate_recommendations(payload.daily_features, payload.user_targets)
    return RecommendationResponse(recommendations=recs)

from typing import Any, Dict, List, Optional

def generate_recommendations(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Temporary stub to unblock API startup.
    Replace with real recommendation logic later.
    """
    return {
        "status": "ok",
        "message": "generate_recommendations stub",
        "input": payload,
        "recommendations": []
    }

