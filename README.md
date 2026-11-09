# PromiseOps

Exception management that protects the **original delivery promise**.
Built by team **NgaChainAILayer2** for the IT Consultant Challenge 2026, Round 2 (build-a-thon), from our Round 1 proposal.

PromiseOps tells a distribution-centre coordinator which orders are about to miss their promise, how long is left to intervene, who owns each case, what was decided and what it cost, and how it ended.
Existing order and warehouse systems keep owning orders, stock and dispatch; PromiseOps only reads from them.

> All company, people and order data in this repository is fictional.
> No Company A data is used.

![Exception queue drawn as a timetable](docs/journey/shots/1-queue-0930.png)

## Contents

- [Submission files](#submission-files)
- [What the MVP does](#what-the-mvp-does)
- [Changes since Round 1](#changes-since-round-1)
- [Quick start](#quick-start)
- [Demo walkthrough](#demo-walkthrough)
- [Project structure](#project-structure)
- [Architecture](#architecture)
- [Technical decisions](#technical-decisions)
- [Tests](#tests)
- [Scripts and documents](#scripts-and-documents)
- [JSON API](#json-api)
- [Not in the MVP](#not-in-the-mvp)

## Submission files

| Deliverable | File |
|---|---|
| MVP demo video | `MVP.mp4` (recorded by the team from `docs/video/video-script.md`; subtitles `docs/video/MVP.srt`; slides `docs/video/slides/`) |
| User journey (2 pages) | `docs/User Journey.pdf` |
| System diagram (2 pages) | `docs/System Diagram.pdf` |
| AI journal | `docs/AI Journal.pdf` (source `docs/AI Journal.docx`) |

## What the MVP does

Every order is drawn as a **course of four controls** on one shared timetable: pick due, dispatch cutoff, last viable dispatch, and the promise.
A red line marks now.
When the line passes a control that has not been confirmed, and the warehouse feed was read after it, an exception opens with one owner.

| Round 1 scope (slides 4, 5, 8) | Where to see it |
|---|---|
| Read order and fulfilment events from existing systems | Source adapter, Data health page, `POST /api/orders`, `POST /api/events` |
| Two exception types: pick not confirmed, dispatch not confirmed | Rules engine, Exception queue |
| Priority queue, one owner, 15-minute response, escalation | Exception queue, exception detail |
| Decisions with evidence; only the shift lead may expedite | Exception detail, activity log |
| PROVE: action cost logged | Cost on every expedite, activity log, Outcomes |
| Outcomes against the original promise, B2B and B2C apart | Outcomes page |
| Pilot decision measures (coverage, actionable alerts, response time) | Pilot scorecard on Outcomes |
| Data freshness guard | Feeds in the rail, stale banner, unknown controls, data-quality tasks |

Rules taken straight from the proposal:

- Priority is time left to the intervention deadline; ties go to B2B.
- One owner per exception and 15 minutes to respond, then automatic escalation to the shift lead.
- One exception per order and cause; a pick alert covers the dispatch alert for the same root cause.
- Only the shift lead can record an expedite, and must log its cost.
- Every outcome needs written evidence.
- The original promise can never be edited, so outcomes stay honest.
- A missing event only counts if the source was read after the milestone; until then the control is shown as unknown.
- When the fulfilment feed is older than 30 minutes, alerts pause and a data-quality task opens.
- An order past its promise without a delivery counts as late (overdue) immediately.
- An alert closed as a false alarm never silences the order: if the pick is still missing when the route leaves, or the dispatch is still missing at the last viable time, the case comes back.
- Nothing is written back to source systems.

The interface is available in **English and Vietnamese**.
System sentences (alert reasons, audit notes, errors) are translated too; text typed by people is never translated.

The landing page at `/` presents the product and plays a recorded, annotated walkthrough in the reader's language.

## Changes since Round 1

The scope is the one we proposed. What changed, and why:

| Round 1 proposal | In the MVP | Why |
|---|---|---|
| Alert at pick + 15 min grace | Alert at the milestone, only if the warehouse feed was read after it; the grace is a market setting (`pick_grace_min`) | The read-after-milestone rule prevents the false alarms the grace was meant to stop and leaves more time to act; the pilot tunes the grace from shadow-mode data |
| 30-minute stale-feed limit | Same limit, plus the read-after-milestone rule | With the limit alone, a feed outage produced 9 false alarms at minute 30 |
| Example timings: pick 08:30, cutoff 10:00, promise 14:00 | Pick 09:30, cutoff 10:00, promise 14:00 | The demo morning starts at 09:00 so it fits the video; same order, cutoff and promise |
| Real order and warehouse feeds | Demo harness (simulated clock, scripted feeds) plus a JSON API for real feeds | No Company A systems or data; the harness replaces only feeds and time, never the engine |
| SSO with role and site access | Demo role switch; API key for integrations | SSO needs Company A's identity provider; planned for the pilot |
| PROVE: action cost logged, cost per outcome | Cost on every expedite; Round 1 scorecard; EUR 25 per prevented late delivery shown as an assumption | Closes the loop to the business case without claiming a measured saving |
| (new) | Timetable view, Vietnamese interface, labelled outcomes API | Time left must be visible at a glance; the team works in Vietnamese; data for the risk model planned after Gate 2 |

## Quick start

Requires Python 3.11 or newer.

```powershell
.\run.ps1
```

or, step by step:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn --app-dir src promiseops.web.app:app --port 8000
```

Open http://127.0.0.1:8000 for the landing page, or http://127.0.0.1:8000/app for the tool.
The database is created and seeded on first start in `var/promiseops.db` (rebuilt automatically if the schema changed).
Set `PROMISEOPS_DB` to use another file, and `PROMISEOPS_API_KEY` to require an `X-API-Key` header on the JSON API.

### Pilot mode

`PROMISEOPS_MODE=pilot` runs the same engine on the wall clock instead of the demo clock:
the database starts empty, OMS/WMS push records and heartbeats to the JSON API, a scheduler runs the rules every minute
(so the 15-minute response timer and the stale-feed guard fire on their own), and the demo controls are switched off (`/sim/*` returns 404).
Use a separate `PROMISEOPS_DB` for it. A demo database is rebuilt when the mode changes, but a pilot database is never wiped:
starting it without `PROMISEOPS_MODE=pilot`, or after a schema change, stops with an error instead.
A scheduler cycle that fails is logged and retried the next minute, so escalation and the stale-feed guard keep running.

```powershell
$env:PROMISEOPS_MODE = "pilot"; $env:PROMISEOPS_DB = "$env:TEMP\pilot.db"; $env:PROMISEOPS_API_KEY = "change-me"
python -m uvicorn --app-dir src promiseops.web.app:app --port 8001
```

## Demo walkthrough

The yellow bar at the bottom of the tool is a **demo harness only**: it replaces real feeds and wall-clock time.
Each recorded human action moves the demo clock by one minute, so the activity log reads like a real shift.
The same steps are recorded with notes in `src/promiseops/web/static/landing/demo-en.webm` and `demo-vi.webm`.

1. Open `/app`, click **Reset scenario**. At 09:00 every order is on course.
2. Click **+30 min**. SE-1042 (B2B site delivery, plasterboard) and SE-1051 missed their 09:30 pick: 30 minutes before the 10:00 route. SE-1042 is first because ties go to B2B.
3. Open **SE-1042**, **Take ownership** (09:30). Expedite is locked for a coordinator, so **Escalate** with the reason (09:31).
4. Switch the role in the rail to **Shift lead**, choose **Expedited by shift lead**, write the evidence, enter cost **10**, **Record outcome** (09:32).
5. Switch back to **DC coordinator**. Open **SE-1051**, **Take ownership**, record **Verified on floor - alert was wrong** with evidence.
6. Click **Simulate feed outage**, then **+30 min** and **+15 min**: the feed turns red, alerts pause, passed controls show as unknown, a data task opens.
7. Click **Resume fulfilment feed** and **+5 min**: the backlog arrives first, then the rules find a real problem, SE-1077 (picked, no vehicle).
8. Open **SE-1077**, **Take ownership**, record **Promise at risk - handed to customer service** with evidence.
9. Go to **Orders** and click **+5 h**: SE-1042 was delivered at 12:32, before its 14:00 promise; SE-1077 arrived at 14:35 and is counted late.
10. Open **Outcomes**: 93.3 % on time against the original promise, 1 late delivery prevented, EUR 25 at the Round 1 assumption against EUR 10 logged, and the Round 1 pilot scorecard.
11. Counterfactual: **Reset scenario**, **+30 min**, **+5 h**, **+1 h**, then **Outcomes**: without anyone acting, SE-1042 arrives at 14:25 and on time falls to 86.7 %.

## Project structure

```
promiseops/
├── src/promiseops/
│   ├── config.py              market settings, roles, outcomes, Round 1 targets and assumptions
│   ├── timeutil.py            UTC storage, local display
│   ├── clock.py               demo clock or wall clock (PROMISEOPS_MODE=pilot)
│   ├── core/
│   │   ├── engine.py          exception rules, freshness guard, escalation
│   │   ├── workflow.py        take ownership, escalate, resolve; role checks; evidence and cost; audit
│   │   ├── kpi.py             outcomes against the original promise, scorecard, value
│   │   ├── queries.py         read models for the screens and the API
│   │   └── timetable.py       course geometry: four controls on one time axis
│   ├── integration/
│   │   ├── ingest.py          source adapter: validation, idempotency, feed reads
│   │   └── simulation.py      demo clock on a 5-minute poll grid, scripted feeds (MVP only)
│   ├── storage/
│   │   ├── db.py              SQLite schema with a version check
│   │   └── seed.py            fictional demo scenario
│   └── web/
│       ├── app.py             application factory, error pages
│       ├── deps.py            settings, database connection, role, language, rendering
│       ├── routes/            pages.py, actions.py, demo.py, api.py
│       ├── i18n.py            English / Vietnamese
│       ├── templates/         Jinja2 pages and the shared course macro
│       └── static/            app.css, landing page assets and walkthrough videos
├── tests/
│   ├── unit/                  rules, escalation, idempotency, stale data, KPIs, poll grid
│   ├── web/                   pages, HTTP actions, role checks, API key, translations
│   └── e2e/                   the core journey in a real browser
├── scripts/                   journey capture, PDF builders, video assets, demo recording, AI journal
├── docs/
│   ├── User Journey.pdf       2 pages
│   ├── System Diagram.pdf     2 pages
│   ├── AI Journal.pdf         the challenge template, filled
│   ├── architecture/          diagram previews and the HTML source
│   ├── journey/               journey screenshots and page previews
│   └── video/                 recording script, English subtitles, slides
├── PRODUCT.md                 product brief used for design work
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── run.ps1
```

## Architecture

One application service with clear modules and one relational database, as proposed for the pilot; no microservices.

```
OMS / WMS ──► JSON API ──► Source adapter ──► SQLite ◄── Rules engine (runs after every poll or accepted record)
                                                 ▲
Coordinator / shift lead ──► Pages, Human actions ──► Workflow (role checks, evidence, cost, audit)
                                 │
                                 └──► Read models: queue order, timetable, outcomes, scorecard
Presenter ──► Demo controls ──► Demo harness (sim clock, scripted feeds) ──► Source adapter     [MVP only]
```

One cycle every 5 minutes, the READ, CHECK, ACT, PROVE stages of Round 1:

1. **Read**: the adapter reads each live feed and records that the read succeeded.
2. **Check**: duplicates are ignored, bad records rejected and logged; if the warehouse feed is stale, or was not read after a milestone, absence-based alerts pause.
3. **Detect**: the two rules create one exception per order and cause, owned by the coordinator, with a 15-minute timer.
4. **Act**: a person decides; an expedite needs the shift lead and a logged cost; every outcome needs evidence; everything lands in the audit log.
5. **Prove**: outcomes are measured against the original promise and the Round 1 pilot targets.

The two-page system diagram (C4 context, then container and components) is built by `scripts/build_system_diagram.py`.

## Technical decisions

| Decision | Choice | Why |
|---|---|---|
| Backend | FastAPI, one process, routers per concern | Matches the proposal: one service with clear modules |
| Database | SQLite with a schema version check | Relational, zero setup for judges; PostgreSQL is the production step |
| Frontend | Server-rendered Jinja2, CSS, a little vanilla JS | No build step, every page testable over HTTP; the timetable is plain HTML and CSS |
| AI in the product | None; labelled outcomes exposed for later | Round 1 argued for explainable rules first; AI was used to build, not inside the product |
| Integration | Read-only adapter, idempotent on source + event id, optional API key | Never risk the systems of record; re-sent data creates no new work |
| Measurement | Overdue orders count as late; percentages from fewer than 10 cases are not judged | Silence must never look like success; small samples must not look like proof |
| Demo clock | Polls on a fixed 5-minute grid; each human action takes 1 simulated minute | Feeds behave like a real adapter; the audit log and response-time KPI read like a real shift |
| Time | Stored in UTC, shown in Europe/Stockholm | Correct across daylight-saving changes |
| Visual direction | Timetable layout with an orienteering course overlay | Chosen by the team from several UI prototypes; see `PRODUCT.md` |

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest
```

46 tests:

- `tests/unit` - rules, escalation, auto-clear, escalation counts as work, one exception per cause, immutable promise, false alarms that turn out wrong come back, idempotent ingestion, stale-feed guard, unknown controls, poll grid, overdue counting, cost logging, scorecard, value.
- `tests/web` - every page renders, HTTP actions and role checks, one simulated minute per action, API validation and API key, source heartbeat, pilot mode on the wall clock without demo controls, a pilot database that a demo restart cannot wipe, a failing scheduler tick that is logged and not fatal, labelled outcomes, 404 page, open-redirect guard, Vietnamese rendering, and checks that every template string and user-facing error has a Vietnamese translation.
- `tests/e2e` - the SE-1042 journey in a real browser, with no console errors allowed.

## Scripts and documents

Run against a running app on a separate port and database so nobody's session is disturbed:

```powershell
$env:PROMISEOPS_DB = "$env:TEMP\demo.db"
python -m uvicorn --app-dir src promiseops.web.app:app --port 8766
```

| Script | Produces |
|---|---|
| `scripts/capture_journey.py [base-url]` | Journey screenshots and the measured numbers in `docs/journey/shots/` |
| `scripts/build_user_journey.py [out.pdf]` | `docs/User Journey.pdf` (2 pages) |
| `scripts/build_system_diagram.py [out.pdf]` | `docs/System Diagram.pdf` (2 pages) |
| `scripts/build_video_assets.py` | Video slides and `MVP.srt` from `docs/video/video-script.md` |
| `scripts/record_demo.py <en or vi> [base-url]` | Annotated walkthrough videos and posters for the landing page |

## JSON API

When `PROMISEOPS_API_KEY` is set, every endpoint except `/api/health` requires the `X-API-Key` header.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/orders` | Receive an order with its promise and milestones; a re-sent order never changes the promise |
| POST | `/api/events` | Receive a fulfilment event; idempotent on `source` + `event_id`; triggers a rules cycle |
| POST | `/api/sources/{id}/heartbeat` | A source that is alive but has nothing new says so, so a quiet feed is not mistaken for a stale one |
| GET | `/api/exceptions` | Open exceptions in priority order |
| GET | `/api/outcomes` | Labelled outcomes: one row per exception with how it ended and the order's result |
| GET | `/api/health` | Mode (demo or pilot), clock, source freshness, authentication mode |

## Not in the MVP

Route optimisation, automatic replenishment, automatic promise changes, write-back to core systems, multi-country rollout, customer messaging, company SSO and a delay-prediction model are out of scope by design.
"Handed to customer service" is recorded as an outcome, not sent.
The late-risk model and an AI summary of case notes remain options after Gate 2, as proposed in Round 1; `/api/outcomes` already provides the labelled data.

Known limits we would close in the pilot build:

- An event that arrives before its order is rejected and logged, not retried; the pilot adds a retry queue.
- A case escalated to the shift lead has no second-level timer; the pilot adds escalation to the operations manager.
- Roles come from a demo switch, not from company SSO with role and site access.
- SQLite and one process; PostgreSQL and a separate scheduler worker are the production step.

## Team and AI use

Team NgaChainAILayer2.
The MVP was built with Claude Code as a pair engineer and reviewed by a separate, strict AI review before submission; the team made the binding decisions (scope, stack, no AI in the product, visual direction, Vietnamese, which review findings to fix).
How AI was used, what was rejected and why, is recorded in `docs/AI Journal.pdf`.
