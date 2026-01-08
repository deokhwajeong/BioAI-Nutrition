import pytesseract
from PIL import Image
import io

def analyze_food_image(image_bytes: bytes) -> str:
    """
    Extract text from food image using OCR.
    """
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Extract text using Tesseract
        text = pytesseract.image_to_string(image)

        return text.strip()

    except Exception as e:
        raise Exception(f"OCR failed: {str(e)}")