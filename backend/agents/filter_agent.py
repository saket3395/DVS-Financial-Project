from config import FILTERS

REQUIRED = ["price", "mcap_cr", "debt_equity", "pbv", "pe", "industry_pe",
            "peg", "roce", "roe", "promoter", "upside_pct", "rsi"]


def passes(stock: dict) -> bool:
    for k in REQUIRED:
        v = stock.get(k)
        if v is None:
            return False
        try:
            float(v)
        except (TypeError, ValueError):
            return False

    f = FILTERS
    return (
        stock["price"] < f["price_max"]
        and stock["mcap_cr"] > f["mcap_min_cr"]
        and stock["debt_equity"] < f["de_max"]
        and stock["pbv"] < f["pbv_max"]
        and stock["pe"] < stock["industry_pe"]
        and f["peg_min"] <= stock["peg"] <= f["peg_max"]
        and stock["roce"] >= f["roce_min"]
        and stock["roe"] >= f["roe_min"]
        and stock["promoter"] > f["promoter_min"]
        and stock["upside_pct"] > f["upside_min"]
        and f["rsi_min"] <= stock["rsi"] <= f["rsi_max"]
    )


def filter_stocks(stocks):
    return [s for s in stocks if passes(s)]
