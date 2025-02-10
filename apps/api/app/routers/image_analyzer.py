import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..services.image_analyzer import analyze_food_image
from ..services.meal_analyzer import analyze_meal
from ..schemas.user_input import AnalyzeMealRequest, AnalyzeMealResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-analyze", tags=["image-analyze"])

@router.post("/upload", response_model=AnalyzeMealResponse)
async def upload_food_image(file: UploadFile = File(...)):
    """
    Upload a food image to analyze nutritional content.

    Uses Tesseract OCR when available, otherwise falls back to
    colour-histogram heuristics for food category estimation.
    """
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read image bytes
    try:
        image_bytes = await file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file: %s", e)
# Updated: 2025-01-30
        raise HTTPException(status_code=400, detail="Could not read uploaded file")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Extract text / food names from image
    try:
        extracted_text = analyze_food_image(image_bytes)
    except Exception as e:
        logger.error("Image analysis engine error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Image analysis failed: {e!s}",
        )

    # Parse text into food items (split by lines)
    items = [{"name": line.strip()} for line in extracted_text.split("\n") if line.strip()]

    if not items:
        raise HTTPException(status_code=400, detail="No food items detected in image")

    # Analyse via meal service
    try:
        result = analyze_meal(AnalyzeMealRequest(items=items))
    except Exception as e:
        logger.error("Meal analysis failed for image items: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Meal analysis failed: {e!s}",
        )

    return result

# Updated: 2025-02-10