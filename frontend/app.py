import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "screener_latest.json"

app = Flask(__name__)


def load_data():
    if not DATA.exists():
        return {"generated_at": None, "count": 0, "stocks": []}
    try:
        return json.loads(DATA.read_text())
    except Exception:
        return {"generated_at": None, "count": 0, "stocks": []}


@app.template_filter("fmt_dt")
def fmt_dt(s):
    if not s:
        return "—"
    try:
        return datetime.fromisoformat(s.replace("Z", "")).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return s


@app.route("/")
def index():
    payload = load_data()
    return render_template("index.html", **payload)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
