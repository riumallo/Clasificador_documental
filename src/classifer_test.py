import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
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

from src.classifier_rules import KEYWORDS, WEIGHTS, classify_text_rules, normalize


def resolve_json_dir(output_dir: Path) -> Path:
    env_name = (os.getenv("JSON_DIR_NAME") or "").strip()
    if env_name:
        return output_dir / env_name
    tesseract_dir = output_dir / "tesseract_json"
    if tesseract_dir.exists():
        return tesseract_dir
    return output_dir / "json"


def resolve_dir(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = (ROOT_DIR / path).resolve()
    return path


def load_corrections(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Corrections file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise ValueError("Unsupported corrections format")


def build_suggestion_pattern(text: str) -> str | None:
    text = normalize(text)
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    if not tokens:
        return None
    escaped = [re.escape(t) for t in tokens]
    return r"\b" + r"\s+".join(escaped) + r"\b"


def collect_suggestions(corrections: list[dict]) -> dict[str, list[str]]:
    per_label: dict[str, list[str]] = defaultdict(list)
    for entry in corrections:
        raw = (entry.get("suggested_keywords") or "").strip()
        if not raw:
            continue
        label = entry.get("new_label") or entry.get("old_label") or "Desconocido"
        pattern = build_suggestion_pattern(raw)
        if not pattern:
            continue
        if pattern not in per_label[label]:
            per_label[label].append(pattern)
    return per_label


def build_keywords_with_suggestions(
    base_keywords: dict[str, list[str]],
    base_weights: dict[str, dict[str, float]],
    suggestions: dict[str, list[str]],
    extra_weight: float,
) -> tuple[dict[str, list[str]], dict[str, dict[str, float]]]:
    keywords = {label: list(patterns) for label, patterns in base_keywords.items()}
    weights = {label: dict(w) for label, w in base_weights.items()}
    for label, patterns in suggestions.items():
        if label not in keywords:
            keywords[label] = []
        if label not in weights:
            weights[label] = {}
        for p in patterns:
            if p not in keywords[label]:
                keywords[label].append(p)
            weights[label][p] = float(extra_weight)
    return keywords, weights


def classify_text_with_keywords(
    text: str,
    keywords: dict[str, list[str]],
    weights: dict[str, dict[str, float]],
    threshold: float,
) -> str:
    t = normalize(text)
    comprobante_overrides = [
        r"\bcomprobante de registro\b",
    ]
    for p in comprobante_overrides:
        if re.search(p, t, flags=re.IGNORECASE):
            return "comprobantes"

    best_label = "Desconocido"
    best_score = 0.0

    for label, patterns in keywords.items():
        matches = []
        label_weights = weights.get(label, {})
        total_weight = 0.0
        for p in patterns:
            w = float(label_weights.get(p, 1.0))
            total_weight += w
            if re.search(p, t, flags=re.IGNORECASE):
                matches.append(p)
        score = sum(float(label_weights.get(p, 1.0)) for p in matches) / max(1.0, total_weight)
        if score > best_score:
            best_score = score
            best_label = label

    if best_score < threshold:
        return "Desconocido"
    return best_label


def evaluate(dataset: list[dict], predict_fn) -> dict:
    total = 0
    correct = 0
    per_label_total = Counter()
    per_label_correct = Counter()
    predictions = {}
    for item in dataset:
        total += 1
        expected = item["expected"]
        per_label_total[expected] += 1
        predicted = predict_fn(item["text"])
        predictions[item["json_name"]] = predicted
        if predicted == expected:
            correct += 1
            per_label_correct[expected] += 1
    accuracy = (correct / total) if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "per_label_total": per_label_total,
        "per_label_correct": per_label_correct,
        "predictions": predictions,
    }


def find_pdf_path(pdf_file: str, input_dir: Path | None, output_dir: Path) -> Path | None:
    if input_dir:
        candidate = input_dir / pdf_file
        if candidate.exists():
            return candidate
    classified_dir = output_dir / "classified"
    if classified_dir.exists():
        for path in classified_dir.rglob(pdf_file):
            return path
    return None


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")


def export_outputs(
    export_dir: Path,
    dataset: list[dict],
    expected_map: dict[str, str],
    base_pred: dict[str, str],
    aug_pred: dict[str, str],
    input_dir: Path | None,
    output_dir: Path,
    copy_pdfs: bool,
) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    base_lines = []
    aug_lines = []
    comparison_lines = []
    missing_pdfs = []

    for item in dataset:
        name = item["json_name"]
        expected = expected_map[name]
        base_label = base_pred.get(name, "Desconocido")
        aug_label = aug_pred.get(name, "Desconocido")
        base_status = "OK" if base_label == expected else "FAIL"
        aug_status = "OK" if aug_label == expected else "FAIL"
        base_lines.append(f"{name}\t{base_label}\t{expected}\t{base_status}")
        aug_lines.append(f"{name}\t{aug_label}\t{expected}\t{aug_status}")

        if base_status == "FAIL" and aug_status == "OK":
            change = "IMPROVED"
        elif base_status == "OK" and aug_status == "FAIL":
            change = "REGRESSED"
        else:
            change = "SAME"
        comparison_lines.append(f"{name}\t{base_label}\t{aug_label}\t{expected}\t{change}")

        if not copy_pdfs:
            continue
        pdf_name = item.get("pdf_file") or f"{Path(name).stem}.pdf"
        pdf_path = find_pdf_path(pdf_name, input_dir, output_dir)
        if not pdf_path:
            missing_pdfs.append(pdf_name)
            continue
        base_dir = export_dir / "base" / base_label
        aug_dir = export_dir / "augmented" / aug_label
        base_dir.mkdir(parents=True, exist_ok=True)
        aug_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, base_dir / pdf_path.name)
        shutil.copy2(pdf_path, aug_dir / pdf_path.name)

    write_lines(export_dir / "test_classification_base.txt", base_lines)
    write_lines(export_dir / "test_classification_augmented.txt", aug_lines)
    write_lines(export_dir / "test_comparison.txt", comparison_lines)

    if missing_pdfs:
        write_lines(export_dir / "missing_pdfs.txt", sorted(set(missing_pdfs)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Test classifier accuracy using corrections.json")
    parser.add_argument("--extra-weight", type=float, default=2.0, help="Weight for suggested keywords")
    parser.add_argument("--threshold", type=float, default=0.12, help="Classification threshold")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items (0 = all)")
    parser.add_argument(
        "--export-dir",
        default="test_classifier",
        help="Folder name under OUTPUT_DIR for test outputs (set to empty to skip)",
    )
    parser.add_argument("--no-copy", action="store_true", help="Do not copy PDFs into test folders")
    args = parser.parse_args()

    load_dotenv()
    output_dir = os.getenv("OUTPUT_DIR")
    if not output_dir:
        raise RuntimeError("OUTPUT_DIR no definido")

    output_dir = resolve_dir(output_dir)
    if not output_dir:
        raise RuntimeError("OUTPUT_DIR no definido")
    input_dir = resolve_dir(os.getenv("INPUT_DIR"))

    json_dir = resolve_json_dir(output_dir)
    if not json_dir.exists():
        raise RuntimeError(f"No existe la carpeta de JSON: {json_dir.resolve()}")

    corrections_path = output_dir / "corrections.json"
    corrections = load_corrections(corrections_path)
    suggestions = collect_suggestions(corrections)

    dataset = []
    missing = []
    for entry in corrections:
        json_name = entry.get("json_file")
        if not json_name:
            continue
        json_path = json_dir / json_name
        if not json_path.exists():
            missing.append(json_name)
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        text = payload.get("text", "")
        expected = entry.get("new_label") or entry.get("old_label") or "Desconocido"
        pdf_file = entry.get("pdf_file") or payload.get("file") or f"{json_path.stem}.pdf"
        dataset.append(
            {
                "json_name": json_name,
                "text": text,
                "expected": expected,
                "pdf_file": pdf_file,
            }
        )

    if args.limit > 0:
        dataset = dataset[: args.limit]

    base_eval = evaluate(dataset, lambda t: classify_text_rules(t).label)

    merged_keywords, merged_weights = build_keywords_with_suggestions(
        KEYWORDS, WEIGHTS, suggestions, args.extra_weight
    )
    augmented_eval = evaluate(
        dataset,
        lambda t: classify_text_with_keywords(t, merged_keywords, merged_weights, args.threshold),
    )

    expected_map = {item["json_name"]: item["expected"] for item in dataset}
    base_pred = base_eval["predictions"]
    aug_pred = augmented_eval["predictions"]

    improved = 0
    regressed = 0
    for name, expected in expected_map.items():
        base_ok = base_pred.get(name) == expected
        aug_ok = aug_pred.get(name) == expected
        if not base_ok and aug_ok:
            improved += 1
        elif base_ok and not aug_ok:
            regressed += 1

    print("Classifier test")
    print(f"Total evaluated: {base_eval['total']}")
    print(f"Base accuracy: {base_eval['accuracy']:.2%} ({base_eval['correct']}/{base_eval['total']})")
    print(
        "Augmented accuracy: "
        f"{augmented_eval['accuracy']:.2%} ({augmented_eval['correct']}/{augmented_eval['total']})"
    )
    print(f"Improved: {improved} | Regressed: {regressed}")

    print("\nAccuracy by label (base -> augmented):")
    labels = sorted(base_eval["per_label_total"].keys())
    for label in labels:
        total = base_eval["per_label_total"][label]
        base_ok = base_eval["per_label_correct"].get(label, 0)
        aug_ok = augmented_eval["per_label_correct"].get(label, 0)
        base_acc = (base_ok / total) if total else 0.0
        aug_acc = (aug_ok / total) if total else 0.0
        print(f"- {label}: {base_acc:.2%} -> {aug_acc:.2%} ({total})")

    if missing:
        print(f"\nMissing JSON files: {len(missing)}")
        for name in missing[:10]:
            print(f"- {name}")

    if args.export_dir:
        export_dir = output_dir / args.export_dir
        export_outputs(
            export_dir,
            dataset,
            expected_map,
            base_pred,
            aug_pred,
            input_dir,
            output_dir,
            not args.no_copy,
        )
        print(f"\nTest outputs saved in: {export_dir.resolve()}")


if __name__ == "__main__":
    main()
