import json
from datetime import datetime

import pandas as pd

from config import OUTPUT_DIR

COLUMNS = ["symbol", "price", "mcap_cr", "pe", "peg", "roce", "roe", "rsi", "upside_pct"]


def write(stocks, sort_by="upside_pct"):
    if not stocks:
        df = pd.DataFrame(columns=COLUMNS)
    else:
        df = pd.DataFrame(stocks)[COLUMNS].sort_values(sort_by, ascending=False)
    df.columns = ["Stock", "Price", "MCap(Cr)", "PE", "PEG", "ROCE", "ROE", "RSI", "Upside%"]

    csv_path = OUTPUT_DIR / "screener_latest.csv"
    json_path = OUTPUT_DIR / "screener_latest.json"
    df.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps({
        "generated_at": datetime.utcnow().isoformat(),
        "count": len(df),
        "stocks": df.to_dict(orient="records"),
    }, default=str, indent=2))
    return csv_path, json_path, df
