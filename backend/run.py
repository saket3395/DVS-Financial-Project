import sys

from agents.automation_agent import setup_logger
from agents.data_agent import fetch_all, fetch_universe
from agents.filter_agent import filter_stocks, passes
from agents.output_agent import write
from agents.validation_agent import clean


def run(limit: int | None = None):
    log = setup_logger()
    try:
        universe = fetch_universe()
        symbols = [u["symbol"] for u in universe]
        if limit:
            symbols = symbols[:limit]
        raw = fetch_all(symbols)
        validated = clean(raw)
        passed = filter_stocks(validated)
        csv_path, json_path, df = write(passed)
        print(f"Scanned: {len(symbols)} | Valid: {len(validated)} | Passed: {len(passed)}")
        print(f"CSV:  {csv_path}\nJSON: {json_path}")
        if not passed and validated:
            from agents.filter_agent import REQUIRED, FILTERS
            missing = {k: 0 for k in REQUIRED}
            for s in validated:
                for k in REQUIRED:
                    if s.get(k) is None:
                        missing[k] += 1
            print("Missing-field counts:", {k: v for k, v in missing.items() if v})
        if not df.empty:
            print(df.to_string(index=False))
    except Exception as e:
        log.exception("run failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(n)
