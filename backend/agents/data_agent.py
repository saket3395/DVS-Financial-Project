import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from io import StringIO
from statistics import median

import pandas as pd
import requests
import yfinance as yf

from config import CACHE_DIR, CACHE_TTL_HOURS, USER_AGENT

NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

YF_TIMEOUT = 10
NEG_CACHE_HOURS = 6


def _cache_path(name): return CACHE_DIR / f"{name}.json"


def _read_cache(name, ttl_hours=CACHE_TTL_HOURS):
    p = _cache_path(name)
    if not p.exists():
        return None
    if datetime.now() - datetime.fromtimestamp(p.stat().st_mtime) > timedelta(hours=ttl_hours):
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_cache(name, data):
    _cache_path(name).write_text(json.dumps(data, default=str))


def fetch_universe(source="nifty500"):
    cache_key = f"universe_{source}"
    cached = _read_cache(cache_key)
    if cached:
        return cached
    url = NIFTY500_URL if source == "nifty500" else NSE_EQUITY_URL
    tickers = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        df = pd.read_csv(StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        sym_col = "Symbol" if "Symbol" in df.columns else "SYMBOL"
        for _, row in df.iterrows():
            sym = str(row[sym_col]).strip()
            tickers[sym] = {"symbol": sym, "exchange": "NSE"}
    except Exception:
        pass
    out = list(tickers.values())
    if out:
        _write_cache(cache_key, out)
    return out


def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _scale_pct(v):
    n = _num(v)
    return n * 100 if n is not None else None


def _rsi14(close: pd.Series):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - 100 / (1 + rs)
    v = rsi.iloc[-1]
    return None if pd.isna(v) else float(v)


def fetch_stock(symbol: str):
    cache_key = f"yfx_{symbol}"
    cached = _read_cache(cache_key)
    if cached:
        return None if cached.get("_miss") else cached
    try:
        t = yf.Ticker(f"{symbol}.NS")
        hist = t.history(period="3mo", interval="1d", timeout=YF_TIMEOUT)
        if hist.empty:
            _write_cache(cache_key, {"_miss": True})
            return None
        close = hist["Close"].astype(float)
        info = getattr(t, "info", {}) or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice") or float(close.iloc[-1])
        mcap = info.get("marketCap")
        target = info.get("targetMeanPrice")
        de = _num(info.get("debtToEquity"))
        mcap_n = _num(mcap)
        out = {
            "symbol": symbol,
            "price": _num(price),
            "mcap_cr": mcap_n / 1e7 if mcap_n else None,
            "pe": _num(info.get("trailingPE")),
            "peg": _num(info.get("pegRatio")),
            "pbv": _num(info.get("priceToBook")),
            "debt_equity": de / 100 if de is not None else None,
            "roe": _scale_pct(info.get("returnOnEquity")),
            "roce": _scale_pct(info.get("returnOnAssets")),
            "promoter": _scale_pct(info.get("heldPercentInsiders")),
            "rsi": _rsi14(close),
            "sector": info.get("sector"),
            "target_mean": _num(target),
        }
        if out["price"] and out["target_mean"]:
            out["upside_pct"] = round((out["target_mean"] - out["price"]) / out["price"] * 100, 2)
        else:
            out["upside_pct"] = None
        _write_cache(cache_key, out)
        return out
    except Exception:
        _write_cache(cache_key, {"_miss": True})
        return None


def assign_industry_pe(stocks):
    by_sector = {}
    for s in stocks:
        sec = s.get("sector")
        pe = _num(s.get("pe"))
        if sec and pe and pe > 0:
            by_sector.setdefault(sec, []).append(pe)
    sector_pe = {sec: median(v) for sec, v in by_sector.items() if v}
    for s in stocks:
        s["industry_pe"] = sector_pe.get(s.get("sector"))
    return stocks


def fetch_all(symbols, max_workers=8):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_stock, s): s for s in symbols}
        for fut in as_completed(futures):
            data = fut.result()
            if data:
                results.append(data)
    return assign_industry_pe(results)
