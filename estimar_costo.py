from __future__ import annotations

import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except Exception as exc:
    print(f"[ERROR] PyMuPDF no disponible: {exc}")
    print("Instala dependencias: pip install -r requirements.txt")
    sys.exit(1)


PRICE_PER_PAGE = 0.0


def _usage() -> None:
    print("Uso: python estimar_costo.py [directorio] [precio_por_pagina] [-r|--recursive]")
    print("Ejemplo: python estimar_costo.py input_pdfs 15.5")
    print("Ejemplo: python estimar_costo.py input_pdfs 15.5 -r")


def _parse_args(argv: list[str]) -> tuple[Path, float, bool]:
    base_dir = Path(__file__).resolve().parent / "input_pdfs"
    price = PRICE_PER_PAGE
    recursive = False
    positional: list[str] = []

    for arg in argv[1:]:
        if arg in ("-r", "--recursive"):
            recursive = True
        else:
            positional.append(arg)

    if len(positional) > 2:
        _usage()
        sys.exit(2)

    if len(positional) >= 1:
        base_dir = Path(positional[0])

    if len(positional) == 2:
        try:
            price = float(positional[1])
        except ValueError:
            print("[ERROR] precio_por_pagina debe ser un numero.")
            _usage()
            sys.exit(2)

    if price < 0:
        print("[ERROR] precio_por_pagina no puede ser negativo.")
        sys.exit(2)

    return base_dir, price, recursive


def _count_pages(pdf_path: Path) -> int:
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def main() -> None:
    base_dir, price, recursive = _parse_args(sys.argv)

    if not base_dir.exists():
        print(f"[ERROR] Directorio no encontrado: {base_dir}")
        sys.exit(1)

    pdfs = sorted(base_dir.rglob("*.pdf") if recursive else base_dir.glob("*.pdf"))
    if not pdfs:
        print(f"[INFO] No hay PDFs en {base_dir}")
        return

    total_pages = 0
    errors = 0

    for pdf in pdfs:
        try:
            pages = _count_pages(pdf)
        except Exception as exc:
            errors += 1
            print(f"[ERROR] No pude leer {pdf}: {exc}")
            continue

        total_pages += pages
        print(f"[OK] {pdf.name} ({pages} paginas)")

    total_cost = total_pages * price
    print(f"[DONE] PDFs: {len(pdfs)} | Errores: {errors}")
    print(f"[DONE] Total paginas: {total_pages}")
    print(f"[DONE] Precio por pagina: {price}")
    print(f"[DONE] Costo estimado: {total_cost}")


if __name__ == "__main__":
    main()
