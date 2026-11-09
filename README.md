# PromiseOps MVP

Exception management that protects the original delivery promise.
Built by team NgaChainAILayer2 for IT Consultant Challenge 2026, Round 2, from our Round 1 proposal.

PromiseOps tells a DC coordinator which orders need action, how long is left to intervene, who owns each case and how it ended.
Existing systems keep owning orders, stock and dispatch; PromiseOps only reads from them.

All data is fictional.
No Company A data is used.

## What the MVP demonstrates

| Round 1 MVP scope | Where to see it |
|---|---|
| Read order and fulfilment events from existing systems | `app/ingest.py`, Data health page, `POST /api/events` |
| Two exception types: pick not confirmed, dispatch not confirmed | `app/engine.py`, Exception queue |
| Priority queue, ownership, response timer and escalation | Exception queue, exception detail page |
| Actions, reasons and outcomes logged | Activity log on every exception |
| KPI against the original promise, B2B and B2C separated | Outcomes page |
| Data freshness guard | Source pills, stale banner, data-quality tasks |

Rules that come straight from the proposal:

- Priority is time left to the intervention deadline; ties go to B2B.
- One owner per exception, 15 minutes to respond, then automatic escalation to the shift lead.
- One exception per order and cause; a pick alert suppresses a dispatch alert for the same root cause.
- Only the shift lead can record an expedite decision.
- Every outcome requires written evidence.
- The original promise can never be edited, so KPIs stay honest.
- A missing event only counts if the source was actually read after the milestone; when the fulfilment feed is older than 30 minutes, alerts pause and a data-quality task opens.
- Nothing is written back to source systems.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000.
The database is created and seeded on first start in `data/promiseops.db`.

## Demo script (about 5 minutes)

The yellow bar at the bottom is a demo harness only: it replaces real feeds and wall-clock time.

1. 09:00 - queue is empty, both feeds fresh.
2. Click **+30 min**. At 09:30, SE-1042 and SE-1051 appear: no pick confirmation, 30 minutes left before the 10:00 route.
3. Open **SE-1051**, take ownership, record **Verified on floor - alert was wrong** with the evidence.
4. Open **SE-1042**, take ownership. Expedite is disabled for a coordinator, so escalate to the shift lead.
5. Switch role to **Shift lead** (top right) and record **Expedited by shift lead**.
6. Click **Simulate feed outage**, then **+30 min** and **+15 min**: the feed turns red, alerts pause, a data-quality task opens and no false alarms are created.
7. Click **Resume fulfilment feed** and **+5 min**: the backlog arrives first, then rules run on fresh data.
8. Go to **Orders**, click **+5 h**: SE-1042 is delivered on time, SE-1077 (no vehicle) is late and counted late.
9. Open **Outcomes**: on-time rate against the original promise, recovered orders, time to ownership, false-alarm rate.

Click **Reset scenario** to start again.
Without step 5, SE-1042 is delivered late, which is the value the product is meant to prove.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest
```

- `tests/test_scenario.py` - rules, escalation, idempotency, immutable promise, stale-data guard, KPI.
- `tests/test_api.py` - pages, HTTP actions, role checks, API validation.
- `tests/test_e2e.py` - the core journey in a real browser.

## Architecture

One application service with clear modules and one relational database, as proposed for the pilot.
No microservices.

```
app/
  ingest.py      adapter: validation, idempotency, source freshness
  engine.py      exception rules, freshness guard, escalation
  workflow.py    human actions with role checks and audit
  kpi.py         outcomes against the original promise
  simulation.py  demo clock and scripted feeds (replaced by scheduled polls in production)
  main.py        web pages and JSON API
  db.py          SQLite schema
  config.py      market configuration (shared engine, local thresholds)
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/events` | Receive a fulfilment event (idempotent on `source` + `event_id`) |
| POST | `/api/orders` | Receive an order with its promise and milestones |
| GET | `/api/exceptions` | Open exceptions in priority order |
| GET | `/api/health` | Clock and source freshness |

## Not in the MVP (by design)

Route optimisation, automatic replenishment, automatic promise changes, write-back to core systems, multi-country rollout, and a delay-prediction model.
AI summaries of case notes are an optional experiment after the pilot, kept out of the core flow.
