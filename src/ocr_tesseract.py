import os
from io import BytesIO

from PIL import Image, ImageEnhance, ImageOps
import pytesseract


def _configure_tesseract_cmd() -> None:
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Basic preprocessing for OCR:
    - grayscale
    - autocontrast
    - contrast boost
    - optional binarization (black/white)
    """
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)

    contrast = float(os.getenv("TESSERACT_CONTRAST", "1.8"))
    gray = ImageEnhance.Contrast(gray).enhance(contrast)

    binarize = os.getenv("TESSERACT_BINARIZE", "1").strip() != "0"
    if binarize:
        threshold = int(os.getenv("TESSERACT_THRESHOLD", "180"))
        gray = gray.point(lambda p: 255 if p > threshold else 0)

    return gray


def ocr_image_bytes_tesseract(png_bytes: bytes, lang: str = "spa") -> str:
    _configure_tesseract_cmd()
    image = Image.open(BytesIO(png_bytes))
    processed = preprocess_image(image)

    psm = os.getenv("TESSERACT_PSM", "6")
    config = f"--oem 3 --psm {psm}"
    text = pytesseract.image_to_string(processed, lang=lang, config=config)
    return (text or "").strip()
