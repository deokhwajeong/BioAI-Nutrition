"""Food image analysis service.

# TODO: expand after research phase
Uses Tesseract OCR when available, otherwise falls back to
basic image metadata analysis with colour-histogram heuristics.
"""

from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

# Attempt to import pytesseract; gracefully degrade if missing.
try:
    import pytesseract  # type: ignore[import-untyped]
    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False
    logger.warning("pytesseract not available – OCR disabled, using fallback analysis")

def _estimate_food_from_image(image: Image.Image) -> str:
    """Heuristic food estimation from image colour profile.

    Analyses the dominant colour channels in the image to make a rough
    guess about food categories.  This is intentionally simplistic – it
    exists purely as a graceful fallback when OCR / ML models are absent.
    """
    img_small = image.resize((64, 64)).convert("RGB")
    pixels = list(img_small.getdata())
    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)

    items: list[str] = []

    # Warm hues → likely cooked food / bread / meat
    if avg_r > 140 and avg_g < 130:
        items.append("grilled protein")
    # Green dominant → salad / vegetables
    if avg_g > avg_r and avg_g > avg_b:
        items.append("mixed vegetables")
        items.append("leafy greens")
    # Light / bright → rice / dairy
    if avg_r > 180 and avg_g > 180 and avg_b > 160:
        items.append("steamed rice")
    # Dark → could be soup / stew
    if avg_r < 100 and avg_g < 100:
        items.append("hearty stew")

    if not items:
        items = ["mixed meal"]

    return "\n".join(items)

def analyze_food_image(image_bytes: bytes) -> str:
    """Extract text or identify food from an uploaded image.

    Returns newline-separated food item names.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Path 1: OCR via Tesseract
        if _HAS_TESSERACT:
            try:
                text = pytesseract.image_to_string(image).strip()
                if text and len(text) > 3:
                    return text
            except Exception as ocr_err:
                logger.warning("OCR extraction failed, falling back: %s", ocr_err)

        # Path 2: Colour-histogram heuristic
        return _estimate_food_from_image(image)

    except Exception as e:
        raise Exception(f"Image analysis failed: {e!s}")

# TODO: add comprehensive tests
