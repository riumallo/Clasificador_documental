from src.config import HAS_GCP_CREDENTIALS, OCR_ENGINE, TESSERACT_LANG
from src.pdf_utils import extract_embedded_text, pdf_pages_as_png_bytes


def _ocr_with_vision(png_bytes: bytes) -> str:
    from src.ocr_vision import ocr_image_bytes_vision

    return ocr_image_bytes_vision(png_bytes)


def _ocr_with_tesseract(png_bytes: bytes) -> str:
    from src.ocr_tesseract import ocr_image_bytes_tesseract

    return ocr_image_bytes_tesseract(png_bytes, lang=TESSERACT_LANG)


def _ocr_page(png_bytes: bytes) -> str:
    if OCR_ENGINE == "vision":
        return _ocr_with_vision(png_bytes)

    if OCR_ENGINE == "tesseract":
        return _ocr_with_tesseract(png_bytes)

    if HAS_GCP_CREDENTIALS:
        try:
            return _ocr_with_vision(png_bytes)
        except Exception as exc:
            print(f"[OCR] Vision failed: {exc}. Falling back to Tesseract.")

    return _ocr_with_tesseract(png_bytes)


def extract_text_from_pdf(pdf_path: str, dpi: int = 200) -> str:
    """
    1) If the PDF has embedded text, use it.
    2) Otherwise run OCR per page with the selected engine.
    """
    print("[OCR] Looking for embedded text...")
    embedded = extract_embedded_text(pdf_path)
    if embedded and len(embedded) > 50:
        print(f"[OCR] Embedded text found ({len(embedded)} chars).")
        return embedded

    engine = OCR_ENGINE
    if engine == "auto":
        engine = "vision" if HAS_GCP_CREDENTIALS else "tesseract"
    print(f"[OCR] No embedded text. OCR per page (engine={engine})...")

    pages_text = []
    for page_num, png_bytes in pdf_pages_as_png_bytes(pdf_path, dpi=dpi):
        print(f"[OCR] Page {page_num}: sending to OCR...")
        t = _ocr_page(png_bytes)
        if t:
            print(f"[OCR] Page {page_num}: received {len(t)} chars.")
            pages_text.append(f"\n--- PAGE {page_num} ---\n{t}")
        else:
            print(f"[OCR] Page {page_num}: no text detected.")

    return "\n".join(pages_text).strip()
