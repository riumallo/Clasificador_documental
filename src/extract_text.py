from src.pdf_utils import extract_embedded_text, pdf_pages_as_png_bytes
from src.ocr_vision import ocr_image_bytes_vision

def extract_text_from_pdf(pdf_path: str, dpi: int = 200) -> str:
    """
    1) Si el PDF trae texto embebido, úsalo.
    2) Si no, OCR por páginas con Google Vision.
    """
    print("[OCR] Buscando texto embebido...")
    embedded = extract_embedded_text(pdf_path)
    if embedded and len(embedded) > 50:  # umbral simple
        print(f"[OCR] Texto embebido encontrado ({len(embedded)} chars).")
        return embedded

    print("[OCR] Sin texto embebido. OCR por pagina...")
    # OCR por página
    pages_text = []
    for page_num, png_bytes in pdf_pages_as_png_bytes(pdf_path, dpi=dpi):
        print(f"[OCR] Pagina {page_num}: enviando a Vision...")
        t = ocr_image_bytes_vision(png_bytes)
        if t:
            print(f"[OCR] Pagina {page_num}: recibido {len(t)} chars.")
            pages_text.append(f"\n--- PAGE {page_num} ---\n{t}")
        else:
            print(f"[OCR] Pagina {page_num}: sin texto detectado.")

    return "\n".join(pages_text).strip()
