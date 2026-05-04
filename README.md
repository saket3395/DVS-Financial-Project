# DVS Financial Project

Multi-agent daily stock screener for NSE + BSE listed equities, with a local Flask website to view results. Filters by fundamentals (P/E vs industry, PEG, ROCE, ROE, D/E, PBV, promoter holding), technicals (RSI 14), and analyst upside.

## Setup
```
pip install -r requirements.txt
python backend/run.py            # generate data/screener_latest.{csv,json}
python frontend/app.py           # open http://127.0.0.1:5000
```

## Cron — daily 8 AM
```
0 8 * * * cd "/Users/saket/Desktop/ThinkBridge Partners/DVS Financial Project" && /usr/bin/env python3 backend/run.py >> logs/cron.log 2>&1
```

## Layout
- `backend/` — pipeline (`run.py`, `config.py`, `agents/`)
- `frontend/` — Flask app + templates + CSS
- `data/` — generated CSV + JSON
- `logs/` — error + cron logs

A creation by Dharmil and Saket
