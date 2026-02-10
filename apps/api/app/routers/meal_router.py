"""Router for text-based meal analysis.

Exposes POST /analyze-meal so the frontend can submit
a list of food-item names and receive nutritional data.
"""

from fastapi import APIRouter
from ..schemas.user_input import AnalyzeMealRequest, AnalyzeMealResponse
from ..services.meal_analyzer import analyze_meal

router = APIRouter(tags=["meal-analyze"])


@router.post("/analyze-meal", response_model=AnalyzeMealResponse)
async def analyze_meal_endpoint(payload: AnalyzeMealRequest):
    """Analyze nutritional content of food items by name."""
    return analyze_meal(payload)
