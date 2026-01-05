import json
import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, send_file, url_for

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

APP_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>PDF Review</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f7f7f7; color: #1f2937; }
      header { background: #111827; color: #fff; padding: 12px 16px; }
      .container { padding: 12px 16px; }
      .toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
      .main { display: flex; gap: 12px; margin-top: 12px; height: calc(100vh - 170px); }
      .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }
      .pdf { flex: 1 1 50%; }
      .text { flex: 1 1 50%; display: flex; flex-direction: column; }
      .text pre { flex: 1; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px; overflow: auto; }
      .meta { font-size: 12px; color: #6b7280; margin-top: 8px; }
      .form { margin-top: 8px; display: grid; gap: 8px; }
      .actions { display: flex; gap: 8px; }
      select, input[type="text"] { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; }
      button { padding: 8px 12px; border: none; border-radius: 6px; cursor: pointer; }
      .primary { background: #2563eb; color: #fff; }
      .secondary { background: #6b7280; color: #fff; }
      .nav { display: flex; gap: 6px; align-items: center; }
      .notice { padding: 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 6px; }
      label { font-size: 13px; }
    </style>
  </head>
  <body>
    <header>
      <strong>PDF Review</strong>
    </header>
    <div class="container">
      <div class="toolbar">
        <form method="get" action="{{ url_for('index') }}">
          <label>Filter</label>
          <select name="label">
            <option value="all" {% if label_filter == "all" %}selected{% endif %}>All</option>
            {% for label in labels %}
            <option value="{{ label }}" {% if label_filter == label %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
          <button class="secondary" type="submit">Apply</button>
        </form>
        {% if total_count > 0 %}
        <div class="nav">
          <a href="{{ url_for('index', label=label_filter, i=0) }}">First</a>
          <a href="{{ url_for('index', label=label_filter, i=prev_i) }}">Prev</a>
          <a href="{{ url_for('index', label=label_filter, i=next_i) }}">Next</a>
          <a href="{{ url_for('index', label=label_filter, i=last_i) }}">Last</a>
        </div>
        <div class="meta">{{ index + 1 }} / {{ total_count }}</div>
        {% endif %}
      </div>

      {% if not record %}
        <div class="notice">No documents found for this filter.</div>
      {% else %}
      <div class="main">
        <div class="panel pdf">
          {% if pdf_url %}
            <embed src="{{ pdf_url }}" type="application/pdf" width="100%" height="100%">
          {% else %}
            <div class="notice">PDF not found in output/classified.</div>
          {% endif %}
        </div>
        <div class="panel text">
          <div class="meta">
            <div><strong>JSON:</strong> {{ record.json_name }}</div>
            <div><strong>PDF:</strong> {{ record.pdf_file }}</div>
            <div><strong>Label:</strong> {{ record.label }} | <strong>Score:</strong> {{ record.score }}</div>
          </div>
          <pre>{{ record.text }}</pre>
          <form class="form" method="post" action="{{ url_for('save') }}">
            <input type="hidden" name="json_name" value="{{ record.json_name }}">
            <input type="hidden" name="label_filter" value="{{ label_filter }}">
            <input type="hidden" name="index" value="{{ index }}">
            <input type="hidden" name="old_label" value="{{ record.label }}">

            <label>Is correct?</label>
            <select name="decision">
              <option value="correct" {% if correction and correction.decision == "correct" %}selected{% endif %}>Correct</option>
              <option value="incorrect" {% if correction and correction.decision == "incorrect" %}selected{% endif %}>Incorrect</option>
            </select>

            <label>New label (if incorrect)</label>
            <select name="new_label">
              {% for label in labels %}
              <option value="{{ label }}" {% if correction and correction.new_label == label %}selected{% endif %}>{{ label }}</option>
              {% endfor %}
            </select>

            <label>Suggested keywords</label>
            <input type="text" name="suggested_keywords" value="{{ correction.suggested_keywords if correction else '' }}">

            <div class="actions">
              <button class="secondary" type="submit" name="action" value="save">Save</button>
              <button class="secondary" type="submit" name="action" value="save_prev">Save and prev</button>
              <button class="primary" type="submit" name="action" value="save_next">Save and next</button>
            </div>
          </form>
        </div>
      </div>
      {% endif %}
    </div>
  </body>
</html>
"""


def resolve_json_dir(output_dir: Path) -> Path:
    env_name = (os.getenv("JSON_DIR_NAME") or "").strip()
    if env_name:
        return output_dir / env_name
    tesseract_dir = output_dir / "tesseract_json"
    if tesseract_dir.exists():
        return tesseract_dir
    return output_dir / "json"


def load_index(json_dir: Path) -> list[dict]:
    records = []
    for json_path in sorted(json_dir.glob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        label = payload.get("label") or "Desconocido"
        pdf_file = payload.get("file") or f"{json_path.stem}.pdf"
        records.append(
            {
                "json_name": json_path.name,
                "json_path": json_path,
                "pdf_file": pdf_file,
                "label": label,
                "score": payload.get("score"),
            }
        )
    return records


def load_corrections(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    return []


def upsert_correction(items: list[dict], entry: dict) -> list[dict]:
    for i, existing in enumerate(items):
        if existing.get("json_file") == entry["json_file"]:
            items[i] = entry
            return items
    items.append(entry)
    return items


def create_app() -> Flask:
    load_dotenv()
    output_dir = os.getenv("OUTPUT_DIR")
    if not output_dir:
        raise RuntimeError("OUTPUT_DIR no definido")

    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = (ROOT_DIR / output_dir).resolve()
    json_dir = resolve_json_dir(output_dir)
    if not json_dir.exists():
        raise RuntimeError(f"No existe la carpeta de JSON: {json_dir.resolve()}")

    records = load_index(json_dir)
    record_map = {r["json_name"]: r for r in records}

    labels = list(KEYWORDS.keys()) + ["Desconocido"]
    labels = sorted(set(labels + [r["label"] for r in records]))

    corrections_path = output_dir / "corrections.json"

    app = Flask(__name__)

    def find_pdf_path(record: dict) -> Path | None:
        candidate = output_dir / "classified" / record["label"] / record["pdf_file"]
        if candidate.exists():
            return candidate
        classified_dir = output_dir / "classified"
        if classified_dir.exists():
            for path in classified_dir.rglob(record["pdf_file"]):
                return path
        return None

    @app.route("/")
    def index():
        label_filter = request.args.get("label", "all")
        try:
            index_value = int(request.args.get("i", "0"))
        except ValueError:
            index_value = 0

        if label_filter == "all":
            filtered = records
        else:
            filtered = [r for r in records if r["label"] == label_filter]

        total = len(filtered)
        if total == 0:
            return render_template_string(
                APP_TEMPLATE,
                record=None,
                labels=labels,
                label_filter=label_filter,
                total_count=0,
                index=0,
                prev_i=0,
                next_i=0,
                last_i=0,
            )

        index_value = max(0, min(index_value, total - 1))
        record = filtered[index_value]
        payload = json.loads(record["json_path"].read_text(encoding="utf-8"))
        record_view = {
            **record,
            "text": payload.get("text", ""),
        }

        corrections = load_corrections(corrections_path)
        corrections_map = {c.get("json_file"): c for c in corrections}
        correction = corrections_map.get(record["json_name"])

        pdf_path = find_pdf_path(record)
        pdf_url = url_for("pdf_file", json_name=record["json_name"]) if pdf_path else None

        return render_template_string(
            APP_TEMPLATE,
            record=record_view,
            correction=correction,
            labels=labels,
            label_filter=label_filter,
            total_count=total,
            index=index_value,
            prev_i=max(0, index_value - 1),
            next_i=min(total - 1, index_value + 1),
            last_i=total - 1,
            pdf_url=pdf_url,
        )

    @app.route("/pdf/<json_name>")
    def pdf_file(json_name: str):
        record = record_map.get(json_name)
        if not record:
            return "Not found", 404
        pdf_path = find_pdf_path(record)
        if not pdf_path:
            return "PDF not found", 404
        return send_file(pdf_path, mimetype="application/pdf")

    @app.route("/save", methods=["POST"])
    def save():
        json_name = request.form.get("json_name")
        label_filter = request.form.get("label_filter", "all")
        try:
            index_value = int(request.form.get("index", "0"))
        except ValueError:
            index_value = 0
        action = request.form.get("action", "save")
        old_label = request.form.get("old_label") or "Desconocido"

        decision = request.form.get("decision", "correct")
        new_label = request.form.get("new_label") or old_label
        if decision == "correct":
            new_label = old_label

        suggested = (request.form.get("suggested_keywords") or "").strip()

        record = record_map.get(json_name)
        if not record:
            return redirect(url_for("index", label=label_filter, i=index_value))

        entry = {
            "json_file": json_name,
            "pdf_file": record["pdf_file"],
            "old_label": old_label,
            "new_label": new_label,
            "decision": decision,
            "suggested_keywords": suggested,
            "corrected_at": datetime.now().isoformat(timespec="seconds"),
        }

        items = load_corrections(corrections_path)
        items = upsert_correction(items, entry)
        corrections_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if action == "save_next":
            index_value += 1
        elif action == "save_prev":
            index_value -= 1
            if index_value < 0:
                index_value = 0

        return redirect(url_for("index", label=label_filter, i=index_value))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
