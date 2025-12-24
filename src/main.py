import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from src.config import INPUT_DIR, OUTPUT_DIR, OCR_ENGINE
from src.classifier_rules import classify_text_rules, KEYWORDS
from src.extract_text import extract_text_from_pdf

def ensure_dirs(base_out: str, json_dir_name: str):
    labels = list(KEYWORDS.keys()) + ["Desconocido"]
    Path(base_out, "classified").mkdir(parents=True, exist_ok=True)
    for l in labels:
        Path(base_out, "classified", l).mkdir(parents=True, exist_ok=True)
    Path(base_out, json_dir_name).mkdir(parents=True, exist_ok=True)


def get_json_dir_name() -> str:
    if OCR_ENGINE == "tesseract":
        return "tesseract_json"
    return "json"

def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    json_dir_name = get_json_dir_name()
    ensure_dirs(str(out_dir), json_dir_name)

    pdfs = list(in_dir.glob("*.pdf"))
    if not pdfs:
        print(f"⚠️ No hay PDFs en {in_dir.resolve()}")
        return

    print(f"Procesando {len(pdfs)} PDFs desde {in_dir.resolve()}")

    for pdf in pdfs:
        try:
            print(f"[START] {pdf.name}")
            print("[STEP] Extrayendo texto...")
            text = extract_text_from_pdf(str(pdf))
            print(f"----- OCR TEXT BEGIN: {pdf.name} -----")
            print(text if text else "[empty]")
            print("----- OCR TEXT END -----")
            print("[STEP] Clasificando...")
            result = classify_text_rules(text)

            # guarda json
            print("[STEP] Guardando JSON...")
            payload = {
                "file": pdf.name,
                "text": text,
                "label": result.label,
                "score": result.score,
                "evidence": result.evidence,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            }
            json_path = out_dir / json_dir_name / f"{pdf.stem}.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            # mover/copy
            print("[STEP] Copiando PDF clasificado...")
            dest_pdf = out_dir / "classified" / result.label / pdf.name
            shutil.copy2(pdf, dest_pdf)   # si quieres mover: shutil.move(pdf, dest_pdf)

            print(f"✅ {pdf.name} -> {result.label} (score={result.score:.2f})")
            print(f"[DONE] {pdf.name}")

        except Exception as e:
            print(f"❌ Error con {pdf.name}: {e}")

if __name__ == "__main__":
    main()
