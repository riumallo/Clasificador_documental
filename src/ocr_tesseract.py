import os
from io import BytesIO

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import pytesseract


def _configure_tesseract_cmd() -> None:
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def _env_flag(name: str, default: str = "1") -> bool:
    value = (os.getenv(name) or default).strip().lower()
    return value not in {"0", "false", "no", "off"}


def _env_float(name: str, default: str) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _env_int(name: str, default: str) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return int(default)
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _estimate_skew_angle(image: Image.Image, max_angle: float, step: float) -> float:
    if max_angle <= 0 or step <= 0:
        return 0.0

    gray = image if image.mode == "L" else ImageOps.grayscale(image)
    best_angle = 0.0
    best_score = -1.0

    angles = np.arange(-max_angle, max_angle + step, step)
    for angle in angles:
        rotated = gray.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=255)
        arr = np.array(rotated)
        if arr.ndim == 3:
            arr = arr[:, :, 0]
        bin_arr = arr < 128
        row_sums = np.sum(bin_arr, axis=1)
        if row_sums.size == 0:
            continue
        score = np.sum((row_sums - row_sums.mean()) ** 2)
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    return best_angle


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Basic preprocessing for OCR:
    - grayscale
    - autocontrast
    - contrast boost
    - optional deskew
    - optional binarization (black/white)
    """
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)

    contrast = _env_float("TESSERACT_CONTRAST", "1.8")
    gray = ImageEnhance.Contrast(gray).enhance(contrast)

    binarize = _env_flag("TESSERACT_BINARIZE", "1")
    threshold = _env_int("TESSERACT_THRESHOLD", "180")

    deskew = _env_flag("TESSERACT_DESKEW", "1")
    if deskew:
        max_angle = _env_float("TESSERACT_DESKEW_MAX_ANGLE", "5")
        step = _env_float("TESSERACT_DESKEW_STEP", "0.5")
        scale = _env_float("TESSERACT_DESKEW_SCALE", "0.5")

        skew_img = gray
        if 0 < scale < 1:
            new_size = (
                max(1, int(skew_img.width * scale)),
                max(1, int(skew_img.height * scale)),
            )
            skew_img = skew_img.resize(new_size, Image.BILINEAR)
        skew_img = skew_img.point(lambda p: 255 if p > threshold else 0)
        angle = _estimate_skew_angle(skew_img, max_angle, step)
        if abs(angle) >= 0.1:
            gray = gray.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=255)

    if binarize:
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
