from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
for d in (CACHE_DIR, OUTPUT_DIR, LOG_DIR):
    d.mkdir(exist_ok=True)

FILTERS = {
    "price_max": 1500,
    "mcap_min_cr": 2000,
    "de_max": 1.0,
    "pbv_max": 10.0,
    "peg_min": 0.0,
    "peg_max": 1.5,
    "roce_min": 10.0,
    "roe_min": 10.0,
    "promoter_min": 35.0,
    "upside_min": 10.0,
    "rsi_min": 30.0,
    "rsi_max": 70.0,
}

CACHE_TTL_HOURS = 20
REQUEST_TIMEOUT = 15
MAX_WORKERS = 8
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
