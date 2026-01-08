from fastapi import APIRouter, UploadFile, File, HTTPException
from ..services.image_analyzer import analyze_food_image
from ..schemas.user_input import AnalyzeMealRequest, AnalyzeMealResponse

router = APIRouter(prefix="/image-analyze", tags=["image-analyze"])

@router.post("/upload", response_model=AnalyzeMealResponse)
async def upload_food_image(file: UploadFile = File(...)):
    """
    Upload a food image to analyze nutritional content using OCR.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read image bytes
        image_bytes = await file.read()

        # Extract text from image
        extracted_text = analyze_food_image(image_bytes)

        # Parse text into food items (simple split by lines)
        items = [{"name": line.strip()} for line in extracted_text.split("\n") if line.strip()]

        if not items:
            raise HTTPException(status_code=400, detail="No food items detected in image")

        # Use existing meal analyzer
        from ..services.meal_analyzer import analyze_meal
        result = analyze_meal(AnalyzeMealRequest(items=items))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")