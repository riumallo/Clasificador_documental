import json
import os
import sys
from collections import Counter
from datetime import datetime
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

from src.classifier_rules import classify_text_rules, KEYWORDS


def main():
    load_dotenv()
    output_dir = os.getenv("OUTPUT_DIR")
    if not output_dir:
        raise RuntimeError("OUTPUT_DIR no definido")

    json_dir = Path(output_dir) / "json"
    if not json_dir.exists():
        print(f"No existe la carpeta de JSON: {json_dir.resolve()}")
        return

    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        print(f"No hay JSONs en {json_dir.resolve()}")
        return

    labels = list(KEYWORDS.keys()) + ["Desconocido"]
    counts = Counter()
    summary_lines = []

    print(f"Procesando {len(json_files)} JSONs desde {json_dir.resolve()}")

    for json_path in json_files:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[ERROR] {json_path.name}: {exc}")
            continue

        text = payload.get("text", "")
        if not isinstance(text, str):
            text = "" if text is None else str(text)

        result = classify_text_rules(text)
        payload["label"] = result.label
        payload["score"] = result.score
        payload["evidence"] = result.evidence
        payload["classified_at"] = datetime.now().isoformat(timespec="seconds")

        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        counts[result.label] += 1
        summary_lines.append(f"{json_path.name}\t{result.label}\t{result.score:.2f}")
        print(f"[OK] {json_path.name} -> {result.label} (score={result.score:.2f})")

    summary_path = Path(output_dir) / "json_classification.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"Resumen guardado en: {summary_path.resolve()}")

    print("Totales por clasificacion:")
    for label in labels:
        print(f"- {label}: {counts.get(label, 0)}")


if __name__ == "__main__":
    main()
