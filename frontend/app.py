import json
from datetime import datetime
from pathlib import Path

import yfinance as yf
from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "screener_latest.json"
OHLC_CACHE = ROOT / "cache"
OHLC_CACHE.mkdir(exist_ok=True)

app = Flask(__name__)


def _clean(v):
    if isinstance(v, float):
        return None if v != v or v in (float("inf"), float("-inf")) else v
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    return v


def load_data():
    if not DATA.exists():
        return {"generated_at": None, "count": 0, "stocks": []}
    try:
        return _clean(json.loads(DATA.read_text(), parse_constant=lambda _x: None))
    except Exception:
        return {"generated_at": None, "count": 0, "stocks": []}


def _ohlc_cache_path(ticker: str):
    today = datetime.utcnow().strftime("%Y%m%d")
    return OHLC_CACHE / f"ohlc_{ticker}_{today}.json"


def fetch_ohlc(ticker: str, days: int = 10):
    p = _ohlc_cache_path(ticker)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    try:
        hist = yf.Ticker(f"{ticker}.NS").history(period=f"{max(days, 10)}d", interval="1d")
        if hist.empty:
            return []
        bars = []
        for ts, row in hist.tail(days).iterrows():
            bars.append({
                "time": ts.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
            })
        p.write_text(json.dumps(bars))
        return bars
    except Exception:
        return []


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
    return render_template("index.html")


@app.route("/api/stocks")
def api_stocks():
    return jsonify(load_data())


@app.route("/api/ohlc")
def api_ohlc():
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify([])
    return jsonify(fetch_ohlc(ticker))


if __name__ == "__main__":
    import os
    cert = ROOT / "certs" / "cert.pem"
    key = ROOT / "certs" / "key.pem"
    if os.environ.get("DVS_HTTPS", "1") == "1" and cert.exists() and key.exists():
        ssl_ctx = (str(cert), str(key))
    elif os.environ.get("DVS_HTTPS", "1") == "1":
        ssl_ctx = "adhoc"
    else:
        ssl_ctx = None
    app.run(host="127.0.0.1", port=5000, debug=False, ssl_context=ssl_ctx)
