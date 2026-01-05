from __future__ import annotations

import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except Exception as exc:
    print(f"[ERROR] PyMuPDF no disponible: {exc}")
    print("Instala dependencias: pip install -r requirements.txt")
    sys.exit(1)


MAX_PAGES_DEFAULT = 5


def _usage() -> None:
    print("Uso: python eliminar_pdf.py [directorio] [max_paginas]")
    print("Ejemplo: python eliminar_pdf.py input_pdfs 5")


def _parse_args(argv: list[str]) -> tuple[Path, int]:
    base_dir = Path(__file__).resolve().parent / "input_pdfs"
    max_pages = MAX_PAGES_DEFAULT

    if len(argv) > 3:
        _usage()
        sys.exit(2)

    if len(argv) >= 2:
        base_dir = Path(argv[1])

    if len(argv) == 3:
        try:
            max_pages = int(argv[2])
        except ValueError:
            print("[ERROR] max_paginas debe ser un entero.")
            _usage()
            sys.exit(2)

    return base_dir, max_pages


def _count_pages(pdf_path: Path) -> int:
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def main() -> None:
    base_dir, max_pages = _parse_args(sys.argv)

    if not base_dir.exists():
        print(f"[ERROR] Directorio no encontrado: {base_dir}")
        sys.exit(1)

    pdfs = sorted(base_dir.glob("*.pdf"))
    if not pdfs:
        print(f"[INFO] No hay PDFs en {base_dir}")
        return

    removed = 0
    kept = 0

    for pdf in pdfs:
        try:
            pages = _count_pages(pdf)
        except Exception as exc:
            print(f"[ERROR] No pude leer {pdf.name}: {exc}")
            continue

        if pages > max_pages:
            try:
                pdf.unlink()
                removed += 1
                print(f"[DEL] {pdf.name} ({pages} paginas)")
            except Exception as exc:
                print(f"[ERROR] No pude eliminar {pdf.name}: {exc}")
        else:
            kept += 1
            print(f"[OK] {pdf.name} ({pages} paginas)")

    print(f"[DONE] Eliminados: {removed} | Mantenidos: {kept}")


if __name__ == "__main__":
    main()
