import os

from config import FILTERS

CORE = ["price", "mcap_cr", "rsi", "upside_pct"]
OPTIONAL = ["debt_equity", "pbv", "pe", "peg", "roce", "roe", "promoter"]
REQUIRED = CORE + OPTIONAL + ["industry_pe"]

STRICT = os.environ.get("DVS_STRICT", "0") == "1"


def _f(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def passes(stock: dict) -> bool:
    f = FILTERS
    g = stock.get
    fields = (REQUIRED if STRICT else CORE)
    for k in fields:
        if _f(g(k)) is None:
            return False

    rules = {
        "price": lambda x: x < f["price_max"],
        "mcap_cr": lambda x: x > f["mcap_min_cr"],
        "debt_equity": lambda x: x < f["de_max"],
        "pbv": lambda x: x < f["pbv_max"],
        "pe": lambda x: x < (_f(g("industry_pe")) or 1e18),
        "peg": lambda x: f["peg_min"] <= x <= f["peg_max"],
        "roce": lambda x: x >= f["roce_min"],
        "roe": lambda x: x >= f["roe_min"],
        "promoter": lambda x: x > f["promoter_min"],
        "upside_pct": lambda x: x > f["upside_min"],
        "rsi": lambda x: f["rsi_min"] <= x <= f["rsi_max"],
    }
    for k, rule in rules.items():
        n = _f(g(k))
        if n is None:
            if STRICT:
                return False
            continue
        if not rule(n):
            return False
    return True


def filter_stocks(stocks):
    return [s for s in stocks if passes(s)]
