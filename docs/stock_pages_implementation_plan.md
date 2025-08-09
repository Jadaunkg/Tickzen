# Stock Pages Implementation Plan

This document describes how to add per‑ticker stock analysis pages to the platform (e.g., /AAPL, /AAPL/overview, /AAPL/technical-analysis, /AAPL/forecast, /AAPL/fundamentals, /AAPL/valuation, /AAPL/news). It reuses the existing analytics pipeline in `reporting_tools/report_generator.py` and serves fast server‑rendered pages backed by JSON snapshots. It also covers batch refresh for 1,000+ tickers and a future path to live data and/or a React frontend.

---

## Objectives
- Add SEO‑friendly, modern stock pages for each ticker.
- Reuse current analytics logic; avoid recomputation per request.
- Persist per‑ticker snapshots (JSON) for fast render and caching.
- Batch update snapshots on a rolling schedule within free API limits; toggle to higher frequency with paid APIs later.
- Provide JSON APIs for future interactivity or SPA migration.

---

## High-Level Architecture
- Snapshot builder: calls `_prepare_report_data(...)` and serializes outputs to a JSON file per ticker under `generated_data/stock_snapshots/`.
- Server‑Side Rendering (SSR) pages: Flask blueprints render Jinja templates from the JSON snapshot.
- Optional JSON APIs: expose parts of the snapshot for client‑side charts or a future React UI.
- Scheduler: APScheduler rotates through ticker groups to refresh snapshots while respecting rate limits.
- SEO: sitemap.xml for all ticker routes; meta tags per page.

---

## New Folders and Files

- app/
  - blueprints/
    - stocks/
      - __init__.py
      - routes.py              # SSR page routes
    - stocks_api/
      - __init__.py
      - routes.py              # JSON APIs
  - services/
    - report_data_service.py   # build/read/write per‑ticker snapshots; cache/freshness
    - ticker_universe.py       # load & validate tickers; grouping/rotation; status
  - seo/
    - sitemap.py               # dynamic sitemap.xml
  - static/
    - css/
      - stocks.css             # new modern UI styles
    - js/
      - charts.js              # optional Plotly helpers
  - templates/
    - stocks/
      - base.html              # layout with tabs/nav/ticker switcher
      - overview.html
      - technical_analysis.html
      - forecast.html
      - fundamentals.html
      - valuation.html
      - news.html
      - components/
        - kpis.html
        - forecast_table.html
        - ta_cards.html
        - peer_table.html
        - risk_list.html
- automation_scripts/
  - scheduler.py               # APScheduler entrypoint
  - jobs/
    - update_stock_snapshot.py # job to build a single ticker snapshot
    - backfill_snapshots.py    # bulk backfill for initial set
- generated_data/
  - stock_snapshots/
    - AAPL.json
    - MSFT.json
    - ...
  - stock_snapshots_index.json # optional: freshness/index summary
- config/
  - stock_pages_config.py      # batch sizes, cadence, TTL, API mode & rate limits
- docs/
  - stock_pages_implementation_plan.md  # this file

---

## Routing Map (SSR)

- /<ticker> → redirect to /<ticker>/overview
- /<ticker>/overview
- /<ticker>/technical-analysis
- /<ticker>/forecast
- /<ticker>/fundamentals
- /<ticker>/valuation
- /<ticker>/news (optional; can be disabled initially)

Validation: tickers must be uppercase [A–Z], digits, dash, dot (e.g., BRK.B, RDS-A), sanitized and normalized.

---

## Wiring Blueprints

Register blueprints in `app/main_portal_app.py`:

```python
# app/main_portal_app.py
from flask import Flask

# ...existing imports...
from app.blueprints.stocks.routes import stocks_bp
from app.blueprints.stocks_api.routes import stocks_api_bp

app = Flask(__name__)
# ...existing config...

app.register_blueprint(stocks_bp)
app.register_blueprint(stocks_api_bp, url_prefix='/api/stocks')

# Optionally: sitemap
from app.seo.sitemap import seo_bp
app.register_blueprint(seo_bp)
```

Blueprint skeletons:

```python
# app/blueprints/stocks/__init__.py
from flask import Blueprint
stocks_bp = Blueprint('stocks', __name__, template_folder='../../templates/stocks')
```

```python
# app/blueprints/stocks/routes.py
from flask import render_template, redirect, url_for, abort
from app.blueprints.stocks import stocks_bp
from app.services.report_data_service import get_snapshot
from app.services.ticker_universe import normalize_ticker, is_supported_ticker

@stocks_bp.route('/<ticker>')
def stock_root(ticker):
    t = normalize_ticker(ticker)
    if not is_supported_ticker(t):
        abort(404)
    return redirect(url_for('stocks.overview', ticker=t))

@stocks_bp.route('/<ticker>/overview')
def overview(ticker):
    t = normalize_ticker(ticker)
    if not is_supported_ticker(t):
        abort(404)
    snap = get_snapshot(t)
    return render_template('stocks/overview.html', ticker=t, snap=snap)

@stocks_bp.route('/<ticker>/technical-analysis')
def technical(ticker):
    t = normalize_ticker(ticker)
    if not is_supported_ticker(t):
        abort(404)
    snap = get_snapshot(t)
    return render_template('stocks/technical_analysis.html', ticker=t, snap=snap)

# add forecast, fundamentals, valuation, news similarly
```

```python
# app/blueprints/stocks_api/__init__.py
from flask import Blueprint
stocks_api_bp = Blueprint('stocks_api', __name__)
```

```python
# app/blueprints/stocks_api/routes.py
from flask import jsonify, abort
from app.blueprints.stocks_api import stocks_api_bp
from app.services.report_data_service import get_snapshot
from app.services.ticker_universe import normalize_ticker, is_supported_ticker

@stocks_api_bp.get('/<ticker>/snapshot')
def snapshot(ticker):
    t = normalize_ticker(ticker)
    if not is_supported_ticker(t):
        abort(404)
    snap = get_snapshot(t)
    return jsonify(snap)

# Optional: provide narrower endpoints by slicing the snapshot dict
@stocks_api_bp.get('/<ticker>/technical')
def technical(ticker):
    t = normalize_ticker(ticker)
    if not is_supported_ticker(t):
        abort(404)
    s = get_snapshot(t)
    return jsonify({
        'detailed_ta_data': s.get('detailed_ta_data'),
        'historical_data': s.get('historical_data_min'),  # optional reduced payload
    })
```

---

## Snapshot Service

`app/services/report_data_service.py` encapsulates snapshot building and I/O. It wraps the existing analytics code without changing it.

Responsibilities:
- build_snapshot(ticker): calls `_prepare_report_data(...)` from `reporting_tools/report_generator.py` and converts all values to JSON‑serializable types.
- save_snapshot(ticker, data): write to `generated_data/stock_snapshots/{TICKER}.json`.
- load_snapshot(ticker): read from disk; return `None` if missing or invalid.
- get_snapshot(ticker, force_refresh=False): check staleness vs TTL, optionally trigger background refresh, return cached data.

Serializer helpers:
- DataFrame → list[dict] via `df.to_dict(orient='records')` (down‑sample if large).
- pd.Timestamp/datetime → ISO‐8601 strings.
- NumPy scalars → native Python numbers.
- Decimals → float or string.

Skeleton:

```python
# app/services/report_data_service.py
import os, json, time
from datetime import datetime, timezone, timedelta
import pandas as pd
from reporting_tools.report_generator import _prepare_report_data
from config.stock_pages_config import SNAPSHOT_DIR, SNAPSHOT_TTL_HOURS, SNAPSHOT_DF_MAX_ROWS

os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def _df_to_records(df: pd.DataFrame, max_rows: int | None = None):
    if df is None or df.empty:
        return []
    if max_rows and len(df) > max_rows:
        df = df.tail(max_rows)
    return df.to_dict(orient='records')

def _make_serializable(obj):
    if isinstance(obj, pd.DataFrame):
        return _df_to_records(obj, SNAPSHOT_DF_MAX_ROWS)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.astimezone(timezone.utc).isoformat()
    try:
        import numpy as np
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
    except Exception:
        pass
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    return obj

def build_snapshot(ticker: str, actual, forecast, historical, fundamentals, plot_period_years=3):
    rdata = _prepare_report_data(ticker, actual, forecast, historical, fundamentals, plot_period_years)
    payload = {
        'ticker': ticker,
        'last_generated': datetime.now(timezone.utc).isoformat(),
        'period_label': rdata.get('period_label'),
        'time_col': rdata.get('time_col'),
        'current_price': rdata.get('current_price'),
        'overall_pct_change': rdata.get('overall_pct_change'),
        'sentiment': rdata.get('sentiment'),
        'forecast_horizon_periods': rdata.get('forecast_horizon_periods'),
        'historical_data': _df_to_records(rdata.get('historical_data')),
        'actual_data': _df_to_records(rdata.get('actual_data')),
        'forecast_data': _df_to_records(rdata.get('forecast_data')),
        'monthly_forecast_table_data': _df_to_records(rdata.get('monthly_forecast_table_data')),
        # technical indicators & conclusions
        'detailed_ta_data': _make_serializable(rdata.get('detailed_ta_data')),
        # fundamentals and sections already extracted by your code
        'profile_data': rdata.get('profile_data'),
        'valuation_data': rdata.get('valuation_data'),
        'financial_health_data': rdata.get('financial_health_data'),
        'profitability_data': rdata.get('profitability_data'),
        'dividends_data': rdata.get('dividends_data'),
        'analyst_info_data': rdata.get('analyst_info_data'),
        'total_valuation_data': rdata.get('total_valuation_data'),
        'share_statistics_data': rdata.get('share_statistics_data'),
        'financial_efficiency_data': rdata.get('financial_efficiency_data'),
        'stock_price_stats_data': rdata.get('stock_price_stats_data'),
        'short_selling_data': rdata.get('short_selling_data'),
        'peer_comparison_data': rdata.get('peer_comparison_data'),
        'risk_items': rdata.get('risk_items'),
        'data_driven_observations': rdata.get('data_driven_observations'),
    }
    return _make_serializable(payload)

def _snapshot_path(ticker: str):
    return os.path.join(SNAPSHOT_DIR, f"{ticker}.json")

def save_snapshot(ticker: str, data: dict):
    with open(_snapshot_path(ticker), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_snapshot(ticker: str) -> dict | None:
    try:
        with open(_snapshot_path(ticker), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def is_stale(snapshot: dict) -> bool:
    try:
        ts = snapshot.get('last_generated')
        if not ts:
            return True
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        age = datetime.now(timezone.utc) - dt
        return age > timedelta(hours=SNAPSHOT_TTL_HOURS)
    except Exception:
        return True

def get_snapshot(ticker: str, force_refresh: bool = False) -> dict:
    snap = load_snapshot(ticker)
    if snap and not force_refresh and not is_stale(snap):
        return snap
    # Lazy: return old snap if exists; a scheduler job keeps them fresh.
    # Optionally: enqueue a refresh task here.
    return snap or {'ticker': ticker, 'error': 'Snapshot not available'}
```

Snapshot JSON example (truncated):

```json
{
  "ticker": "AAPL",
  "last_generated": "2025-08-09T12:00:00Z",
  "period_label": "Month",
  "time_col": "Period",
  "current_price": 225.12,
  "overall_pct_change": 8.7,
  "sentiment": "Neutral to Bullish",
  "forecast_horizon_periods": 12,
  "historical_data": [{"Date": "2024-08-01", "Close": 192.2, "Volume": 123456789}, ...],
  "monthly_forecast_table_data": [{"Period": "2025-01", "Low": 190.0, "Average": 205.0, "High": 220.0}],
  "detailed_ta_data": {"RSI_14": 58.2, "SMA_50": 210.4, "SMA_200": 195.1, "MACD_Line": 1.2, ...},
  "profile_data": {"Sector": "Technology", ...},
  "valuation_data": {"Forward P/E": "22.5x", ...},
  "risk_items": ["RSI high", "Current price below SMA 50"],
  "data_driven_observations": ["Undervalued vs growth & D/E"]
}
```

---

## Ticker Universe Service

`app/services/ticker_universe.py`:
- load `all-us-tickers.json` or a curated subset.
- `normalize_ticker(s)`: uppercase, strip whitespace, allow [A–Z0–9.–].
- `is_supported_ticker(t)`: membership test.
- `groups_for_rotation(n_groups)`: deterministic partition (e.g., hash mod n).

```python
# app/services/ticker_universe.py
import json, re, os
from config.stock_pages_config import TICKER_UNIVERSE_PATH

_VALID = re.compile(r'^[A-Z0-9][A-Z0-9\.-]*$')

with open(TICKER_UNIVERSE_PATH, 'r', encoding='utf-8') as f:
    _UNIVERSE = {t.strip().upper() for t in json.load(f)}

def normalize_ticker(s: str) -> str:
    return s.strip().upper()

def is_supported_ticker(t: str) -> bool:
    return bool(_VALID.match(t)) and t in _UNIVERSE

def groups_for_rotation(n: int):
    buckets = [list() for _ in range(n)]
    for t in sorted(_UNIVERSE):
        buckets[hash(t) % n].append(t)
    return buckets
```

---

## Scheduler and Jobs

Use APScheduler’s `BackgroundScheduler` within the web dyno/process or as a separate worker (recommended for heavy loads).

`scheduler.py`:

```python
# automation_scripts/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from automation_scripts.jobs.update_stock_snapshot import update_group
from app.services.ticker_universe import groups_for_rotation
from config.stock_pages_config import ROTATION_GROUPS, CRON_MINUTE, CRON_HOUR

sched = BackgroundScheduler(timezone='UTC')

_GROUPS = groups_for_rotation(ROTATION_GROUPS)

# Schedule each group hourly (stagger by minute)
for i, group in enumerate(_GROUPS):
    sched.add_job(update_group, 'cron', hour=CRON_HOUR, minute=(CRON_MINUTE + i) % 60, args=[group], id=f'grp-{i}', max_instances=1, coalesce=True, replace_existing=True)

sched.start()
```

`jobs/update_stock_snapshot.py`:

```python
# automation_scripts/jobs/update_stock_snapshot.py
from app.services.report_data_service import build_snapshot, save_snapshot
# your existing data fetchers for actual/forecast/historical/fundamentals
from reporting_tools import report_generator as rg

# TODO: wire your real data providers

def fetch_inputs(ticker: str):
    actual = None
    forecast = None
    historical = None
    fundamentals = None
    return actual, forecast, historical, fundamentals

def update_group(tickers: list[str]):
    for t in tickers:
        try:
            actual, forecast, historical, fundamentals = fetch_inputs(t)
            snap = build_snapshot(t, actual, forecast, historical, fundamentals)
            save_snapshot(t, snap)
        except Exception as e:
            # log and continue; add exponential backoff if rate-limited
            print(f"[Scheduler] Failed {t}: {e}")
```

Backfill one‑time:

```python
# automation_scripts/jobs/backfill_snapshots.py
from app.services.ticker_universe import groups_for_rotation
from .update_stock_snapshot import update_group

def backfill_all(n_groups=24):
    for group in groups_for_rotation(n_groups):
        update_group(group)
```

Rate limiting & retries:
- Insert `time.sleep()` or token bucket between API calls.
- Track provider errors; exponential backoff on 429/5xx.
- Persist last success per ticker in `stock_snapshots_index.json` for visibility.

---

## Templates and UI

Base layout (`templates/stocks/base.html`):
- Sticky header with ticker search and section tabs (Overview, Technical, Forecast, Fundamentals, Valuation, News).
- Load `stocks.css` and optional `charts.js`.

Overview page (`templates/stocks/overview.html`) consumes `snap`:

```html
{% extends 'stocks/base.html' %}
{% block content %}
<section class="hero">
  <h1>{{ ticker }} — Stock Overview</h1>
  <div class="kpis">
    {% include 'stocks/components/kpis.html' %}
  </div>
</section>
<section class="forecast">
  <h2>Price Forecast</h2>
  <div id="forecast-chart" data-series='{{ snap.monthly_forecast_table_data | tojson }}' data-time-col='{{ snap.time_col }}'></div>
  {% include 'stocks/components/forecast_table.html' %}
</section>
<section class="risks">
  <h2>Risk Factors</h2>
  {% include 'stocks/components/risk_list.html' %}
</section>
{% endblock %}
```

Technical Analysis (`templates/stocks/technical_analysis.html`):
- Cards for RSI, MACD, Bollinger; show current values from `snap.detailed_ta_data`.
- Optional client‑side Plotly charts using `historical_data` downsampled series.

CSS (`app/static/css/stocks.css`):
- Responsive grid, cards, tabs, consistent spacing, dark/light themes.

Client charts (`app/static/js/charts.js`):
- Read `data-series` attributes, build Plotly traces client‑side to avoid heavy HTML chart payloads.

---

## SEO

- Dynamic sitemap: `app/seo/sitemap.py`:

```python
# app/seo/sitemap.py
from flask import Blueprint, Response, url_for
from app.services.ticker_universe import _UNIVERSE

seo_bp = Blueprint('seo', __name__)

@seo_bp.route('/sitemap.xml')
def sitemap():
    urls = []
    for t in sorted(_UNIVERSE):
        urls += [f"/{t}/overview", f"/{t}/technical-analysis", f"/{t}/forecast", f"/{t}/fundamentals", f"/{t}/valuation"]
    xml = ["<?xml version='1.0' encoding='UTF-8'?>", "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"]
    for u in urls:
        xml.append(f"  <url><loc>{{}}</loc></url>".format(url_for('stocks.overview', ticker='T', _external=True)).replace('/T/overview', u))
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype='application/xml')
```

- Meta tags: title/description from `snap.profile_data` + `snap.sentiment`.
- Canonical URLs: include `<link rel="canonical" href="{{ request.url }}"/>` once per page.

---

## Config

`config/stock_pages_config.py` example:

```python
import os
ROOT = os.path.dirname(os.path.dirname(__file__))
SNAPSHOT_DIR = os.path.join(ROOT, 'generated_data', 'stock_snapshots')
TICKER_UNIVERSE_PATH = os.path.join(ROOT, 'all-us-tickers.json')
SNAPSHOT_TTL_HOURS = 24
SNAPSHOT_DF_MAX_ROWS = 1000   # limit payload size
ROTATION_GROUPS = 24          # roughly hourly waves per day
CRON_HOUR = '*'               # every hour
CRON_MINUTE = 0
API_MODE = 'free'             # or 'premium'
RATE_LIMIT_PER_MIN = 50       # tune per provider
```

Dependencies to add in `requirements.txt`:
- APScheduler
- Flask-Caching (optional)
- Flask-Cors (only if serving a separate frontend origin)

---

## Performance & Caching
- Disk snapshots: fast local reads; keep payloads compact.
- Downsample long historical series to avoid heavy JSON.
- HTTP caching: set `Cache-Control` for static, use ETag/Last‑Modified for snapshot endpoints.
- Template fragments: cache top panels with Flask‑Caching if needed.

---

## Error Handling & UX
- If snapshot missing or stale: show badge “Updated X hours ago. Refresh scheduled.”
- If specific sections unavailable: render placeholders with muted styling.
- 404 for unsupported tickers; suggestions/autocomplete for valid ones.

---

## Testing
- Unit tests: serializer, staleness logic, ticker validation.
- Integration tests: blueprint routes 200/404; snapshot API contract.
- Job tests: update_group handles rate limit errors gracefully, persists files.

---

## Phased Rollout
1) Phase 1 (SSR foundation)
- Implement `report_data_service.py`, `ticker_universe.py`.
- Create blueprints, templates with minimal Overview & Technical pages.
- Backfill snapshots for initial 1000 tickers.
- Add sitemap.xml.

2) Phase 2 (Automation & breadth)
- Add APScheduler jobs and rotation.
- Add valuation/fundamentals pages.
- Introduce JSON APIs and client‑side charts for heavy sections.

3) Phase 3 (Polish & scale)
- UI polish, responsive design, accessibility.
- In‑memory cache for hot tickers; CDN for static.

4) Phase 4 (Optional React)
- Add `frontend/` (Vite + React) that consumes `/api/stocks/...`.
- Gradually replace SSR sections or run as SPA; keep SSR for SEO if desired via hybrid rendering.

5) Phase 5 (Paid/live data)
- Flip `API_MODE = 'premium'`; increase refresh cadence for top tickers.
- Add selective near‑real‑time updates (e.g., top 100 tickers every 5–15 minutes).

---

## Optional: React Frontend (Future‑proofing)
Structure:
- `frontend/` with Vite + React (TypeScript recommended).
- Build outDir → `app/static/react/` or `app/frontend_dist/`.
- Dev proxy → Flask backend to avoid CORS.
- Production: serve `index.html` with IIS rewrite to SPA, or continue SSR and progressively enhance sections.

Key benefit: the JSON APIs already designed let you adopt React later without reworking the backend.

---

## Notes on Deployment (Windows/IIS)
- `web.config` may need URL rewrites only if serving an SPA; for SSR routes this is typically fine as‑is.
- Ensure `generated_data/stock_snapshots/` is writeable in your hosting environment.
- If using multiple workers, consider a shared storage (Azure Files/S3/etc.) or keep scheduler as a single worker.

---

## Work Breakdown Checklist
- [ ] Create services (`report_data_service.py`, `ticker_universe.py`)
- [ ] Add blueprints (`stocks`, `stocks_api`), register in app
- [ ] Build minimal templates and CSS
- [ ] Backfill initial 1000 snapshots
- [ ] Add sitemap.xml
- [ ] Add APScheduler rotation & jobs
- [ ] Expose JSON APIs and client charts
- [ ] Optimize caching & payload sizes
- [ ] Add tests
- [ ] Prepare for optional React migration
