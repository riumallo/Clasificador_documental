import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        env_path = ROOT_DIR / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)

from src.classifier_rules import KEYWORDS


def resolve_json_dir(output_dir: Path) -> Path:
    env_name = (os.getenv("JSON_DIR_NAME") or "").strip()
    if env_name:
        return output_dir / env_name
    tesseract_dir = output_dir / "tesseract_json"
    if tesseract_dir.exists():
        return tesseract_dir
    return output_dir / "json"


def clear_classified_dir(classified_dir: Path) -> None:
    if not classified_dir.exists():
        return
    for path in classified_dir.glob("**/*"):
        if path.is_file():
            path.unlink()


def main() -> None:
    load_dotenv()
    input_dir = os.getenv("INPUT_DIR")
    output_dir = os.getenv("OUTPUT_DIR")
    if not input_dir or not output_dir:
        raise RuntimeError("INPUT_DIR o OUTPUT_DIR no definidos")

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    json_dir = resolve_json_dir(output_dir)
    if not json_dir.exists():
        print(f"No existe la carpeta de JSON: {json_dir.resolve()}")
        return

    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        print(f"No hay JSONs en {json_dir.resolve()}")
        return

    classified_dir = output_dir / "classified"
    labels = list(KEYWORDS.keys()) + ["Desconocido"]
    for label in labels:
        (classified_dir / label).mkdir(parents=True, exist_ok=True)

    print(f"Limpiando carpetas en {classified_dir.resolve()}")
    clear_classified_dir(classified_dir)

    counts = Counter()
    missing = []

    print(f"Copiando PDFs desde {input_dir.resolve()} usando {json_dir.resolve()}")
    for json_path in json_files:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[ERROR] {json_path.name}: {exc}")
            continue

        label = payload.get("label") or "Desconocido"
        file_name = payload.get("file") or f"{json_path.stem}.pdf"

        src_pdf = input_dir / file_name
        if not src_pdf.exists():
            missing.append(file_name)
            print(f"[WARN] No existe el PDF: {src_pdf}")
            continue

        dest_dir = classified_dir / label
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_pdf = dest_dir / src_pdf.name
        shutil.copy2(src_pdf, dest_pdf)
        counts[label] += 1
        print(f"[OK] {src_pdf.name} -> {label}")

    print("Totales por clasificacion:")
    for label in labels:
        print(f"- {label}: {counts.get(label, 0)}")

    if missing:
        print("PDFs no encontrados en input:")
        for name in sorted(set(missing)):
            print(f"- {name}")


if __name__ == "__main__":
    main()
