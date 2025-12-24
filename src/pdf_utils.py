import fitz  # pymupdf

def extract_embedded_text(pdf_path: str) -> str:
    """Extrae texto si el PDF tiene texto seleccionable (no escaneado)."""
    doc = fitz.open(pdf_path)
    chunks = []
    for page in doc:
        t = page.get_text("text") or ""
        if t.strip():
            chunks.append(t)
    doc.close()
    return "\n".join(chunks).strip()

def pdf_pages_as_png_bytes(pdf_path: str, dpi: int = 200):
    """
    Genera bytes PNG por página.
    dpi 200-300 suele ser buen equilibrio entre calidad y costo/tiempo.
    """
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        yield i + 1, pix.tobytes("png")

    doc.close()
