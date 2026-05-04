import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

from config import CACHE_DIR, CACHE_TTL_HOURS, MAX_WORKERS, REQUEST_TIMEOUT, USER_AGENT

NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
BSE_EQUITY_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListOfScripCodeXmlw/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
SCREENER_URL = "https://www.screener.in/company/{ticker}/consolidated/"
SCREENER_FALLBACK = "https://www.screener.in/company/{ticker}/"

HEADERS = {"User-Agent": USER_AGENT}


def _cache_path(name: str):
    return CACHE_DIR / f"{name}.json"


def _read_cache(name: str):
    p = _cache_path(name)
    if not p.exists():
        return None
    age = datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
    if age > timedelta(hours=CACHE_TTL_HOURS):
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_cache(name: str, data):
    _cache_path(name).write_text(json.dumps(data, default=str))


def fetch_universe():
    cached = _read_cache("universe")
    if cached:
        return cached
    tickers = {}
    try:
        r = requests.get(NSE_EQUITY_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        df = pd.read_csv(StringIO(r.text))
        for _, row in df.iterrows():
            sym = str(row["SYMBOL"]).strip()
            tickers[sym] = {"symbol": sym, "name": str(row[" NAME OF COMPANY"]).strip(), "exchange": "NSE"}
    except Exception:
        pass
    try:
        r = requests.get("https://www.bseindia.com/corporates/List_Scrips.html", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        # BSE list often unreliable to scrape; fall back to NSE-only union
    except Exception:
        pass
    out = list(tickers.values())
    _write_cache("universe", out)
    return out


def _to_float(s):
    if s is None:
        return None
    s = re.sub(r"[^\d.\-]", "", str(s))
    try:
        return float(s) if s not in ("", ".", "-") else None
    except ValueError:
        return None


def _parse_screener(html: str):
    soup = BeautifulSoup(html, "lxml")
    data = {}
    for li in soup.select("ul#top-ratios li"):
        name_el = li.select_one(".name")
        val_el = li.select_one(".value .number") or li.select_one(".value")
        if not name_el or not val_el:
            continue
        key = name_el.get_text(" ", strip=True).lower()
        val = val_el.get_text(" ", strip=True)
        data[key] = val

    out = {
        "price": _to_float(data.get("current price")),
        "mcap_cr": _to_float(data.get("market cap")),
        "pe": _to_float(data.get("stock p/e")),
        "pbv": _to_float(data.get("price to book value")) or _to_float(data.get("book value")),
        "roce": _to_float(data.get("roce")),
        "roe": _to_float(data.get("roe")),
        "industry_pe": _to_float(data.get("industry p/e")),
        "debt_equity": None,
        "promoter": None,
    }

    for sec in soup.select("section.card"):
        h = sec.select_one("h2")
        if not h:
            continue
        title = h.get_text(strip=True).lower()
        if "balance sheet" in title or "ratios" in title:
            for tr in sec.select("table tr"):
                tds = tr.select("td")
                if len(tds) < 2:
                    continue
                k = tds[0].get_text(strip=True).lower()
                vals = [_to_float(td.get_text()) for td in tds[1:]]
                vals = [v for v in vals if v is not None]
                if not vals:
                    continue
                if "debt / equity" in k or "debt/equity" in k:
                    out["debt_equity"] = vals[-1]

    for sec in soup.select("section#shareholding, div#shareholding, section.card"):
        text = sec.get_text(" ", strip=True).lower()
        if "promoter" in text and "%" in text:
            m = re.search(r"promoter[s]?\s*[^\d]*([\d.]+)\s*%", text)
            if m:
                out["promoter"] = _to_float(m.group(1))
                break

    peg = _to_float(data.get("peg ratio")) or _to_float(data.get("peg"))
    out["peg"] = peg
    return out


def fetch_screener(symbol: str):
    cache_key = f"screener_{symbol}"
    cached = _read_cache(cache_key)
    if cached:
        return cached
    for url in (SCREENER_URL.format(ticker=symbol), SCREENER_FALLBACK.format(ticker=symbol)):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            data = _parse_screener(r.text)
            if data.get("price"):
                _write_cache(cache_key, data)
                return data
        except Exception:
            continue
    return None


def fetch_yf(symbol: str):
    cache_key = f"yf_{symbol}"
    cached = _read_cache(cache_key)
    if cached:
        return cached
    try:
        t = yf.Ticker(f"{symbol}.NS")
        hist = t.history(period="3mo", interval="1d")
        if hist.empty:
            return None
        close = hist["Close"].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-9)
        rsi = 100 - 100 / (1 + rs)
        info = getattr(t, "info", {}) or {}
        out = {
            "rsi": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
            "price_yf": float(close.iloc[-1]),
            "target_mean": info.get("targetMeanPrice"),
        }
        _write_cache(cache_key, out)
        return out
    except Exception:
        return None


def fetch_stock(symbol: str):
    s = fetch_screener(symbol)
    y = fetch_yf(symbol)
    if not s and not y:
        return None
    out = {"symbol": symbol}
    if s:
        out.update(s)
    if y:
        out.update(y)
    price = out.get("price") or out.get("price_yf")
    target = out.get("target_mean")
    if price and target and price > 0:
        out["upside_pct"] = round((float(target) - float(price)) / float(price) * 100, 2)
    else:
        out["upside_pct"] = None
    return out


def fetch_all(symbols, max_workers=MAX_WORKERS):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_stock, s): s for s in symbols}
        for fut in as_completed(futures):
            data = fut.result()
            if data:
                results.append(data)
    return results
