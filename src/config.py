import os
from dotenv import load_dotenv

load_dotenv()

GCP_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
OCR_ENGINE = (os.getenv("OCR_ENGINE") or "vision").strip().lower()
TESSERACT_LANG = (os.getenv("TESSERACT_LANG") or "spa").strip()

_OCR_DPI_RAW = (os.getenv("OCR_DPI") or "300").strip()
try:
    OCR_DPI = int(_OCR_DPI_RAW)
except ValueError as exc:
    raise RuntimeError(" OCR_DPI debe ser un entero") from exc

HAS_GCP_CREDENTIALS = bool(GCP_CREDENTIALS and os.path.exists(GCP_CREDENTIALS))

if OCR_ENGINE not in {"vision", "tesseract", "auto"}:
    raise RuntimeError(" OCR_ENGINE invalido: use vision, tesseract o auto")

if not INPUT_DIR or not OUTPUT_DIR:
    raise RuntimeError(" INPUT_DIR o OUTPUT_DIR no definidos")

if OCR_ENGINE == "vision" and not HAS_GCP_CREDENTIALS:
    raise RuntimeError(" No se encontro el JSON de Google Vision")
