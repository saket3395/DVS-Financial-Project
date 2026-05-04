RANGES = {
    "price": (0.1, 1_000_000),
    "mcap_cr": (1, 50_000_000),
    "debt_equity": (0, 50),
    "pbv": (0, 1000),
    "pe": (0.1, 10_000),
    "industry_pe": (0.1, 10_000),
    "peg": (-50, 50),
    "roce": (-1000, 1000),
    "roe": (-1000, 1000),
    "promoter": (0, 100),
    "upside_pct": (-1000, 10_000),
    "rsi": (0, 100),
}


def validate(stock: dict) -> bool:
    for k, (lo, hi) in RANGES.items():
        v = stock.get(k)
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            return False
        if not (lo <= v <= hi):
            return False
    if stock.get("pe") and stock.get("industry_pe") == 0:
        return False
    return True


def clean(stocks):
    return [s for s in stocks if validate(s)]
