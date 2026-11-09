"""HTTP-level checks: pages render, actions redirect with feedback, API validates input and access."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from promiseops.web import app as main
    from promiseops.web import deps

    monkeypatch.setattr(deps.settings, "db_path", tmp_path / "api.db")
    monkeypatch.setattr(deps.settings, "api_key", None)
    with TestClient(main.app) as c:
        yield c


def now_utc(client) -> str:
    return client.get("/api/health").json()["now"]


def test_pages_render(client):
    for path in ["/", "/app", "/orders", "/kpi", "/data", "/app?view=mine"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "PromiseOps" in r.text


def test_full_journey_over_http(client):
    client.post("/sim/advance", data={"minutes": 30, "next": "/app"})
    r = client.get("/api/exceptions")
    ids = {x["order_id"]: x["id"] for x in r.json()["open"]}
    assert set(ids) == {"SE-1042", "SE-1051"}
    xid = ids["SE-1042"]

    r = client.post(f"/exceptions/{xid}/ack", follow_redirects=False)
    assert r.status_code == 303

    # Coordinator is blocked from expediting, with a helpful message.
    r = client.post(f"/exceptions/{xid}/resolve", data={"resolution": "EXPEDITED", "note": "x", "cost": "0"})
    assert "Escalate to the shift lead" in r.text

    client.post(f"/exceptions/{xid}/escalate", data={"note": "Not picked"})
    client.post("/role", data={"role": "shift_lead", "next": "/app"})
    r = client.post(f"/exceptions/{xid}/resolve", data={"resolution": "EXPEDITED", "note": "Priority pick"})
    assert "Log the intervention cost" in r.text
    r = client.post(f"/exceptions/{xid}/resolve",
                    data={"resolution": "EXPEDITED", "note": "Priority pick", "cost": "40"})
    assert "Outcome recorded" in r.text
    detail = client.get(f"/exceptions/{xid}").text
    assert "Expedited by shift lead" in detail
    assert "EUR 40" in detail


def test_each_human_action_takes_one_simulated_minute(client):
    client.post("/sim/advance", data={"minutes": 30, "next": "/app"})
    xid = client.get("/api/exceptions").json()["open"][0]["id"]
    assert now_utc(client).endswith("08:30:00Z")  # 09:30 in Stockholm
    client.post(f"/exceptions/{xid}/ack")
    assert now_utc(client).endswith("08:31:00Z")
    # A refused action takes no time.
    client.post(f"/exceptions/{xid}/note", data={"note": "  "})
    assert now_utc(client).endswith("08:31:00Z")


def test_queue_ties_go_to_b2b(client):
    client.post("/sim/advance", data={"minutes": 30, "next": "/app"})
    rows = client.get("/api/exceptions").json()["open"]
    assert [r["order_id"] for r in rows] == ["SE-1042", "SE-1051"]  # same deadline; SE-1042 is B2B
    assert rows[0]["customer_type"] == "B2B"


def test_outcomes_page_shows_scorecard_and_overdue(client):
    client.post("/sim/advance", data={"minutes": 330, "next": "/kpi"})  # 14:30
    html = client.get("/kpi").text
    assert "Pilot scorecard" in html
    assert "1 overdue" in html
    assert "Overdue, not delivered" in client.get("/orders").text


def test_api_rejects_bad_event(client):
    r = client.post("/api/events", json={
        "source": "wms", "event_id": "E1", "order_id": "NOPE", "type": "PICK_CONFIRMED",
        "occurred_at": "2026-11-10T08:00:00Z",
    })
    assert r.status_code == 422


def test_api_accepts_event_and_is_idempotent(client):
    body = {"source": "wms", "event_id": "E2", "order_id": "SE-1042", "type": "PICK_CONFIRMED",
            "occurred_at": "2026-11-10T07:55:00Z"}
    assert client.post("/api/events", json=body).json()["outcome"] == "accepted"
    assert client.post("/api/events", json=body).json()["outcome"] == "duplicate"


def test_api_key_is_enforced_when_configured(client, monkeypatch):
    from promiseops.web import deps

    monkeypatch.setattr(deps.settings, "api_key", "s3cret-for-test")
    assert client.get("/api/exceptions").status_code == 401
    assert client.get("/api/exceptions", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/exceptions", headers={"X-API-Key": "s3cret-for-test"}).status_code == 200
    body = {"source": "wms", "event_id": "E3", "order_id": "SE-1042", "type": "PICK_CONFIRMED",
            "occurred_at": "2026-11-10T07:55:00Z"}
    assert client.post("/api/events", json=body).status_code == 401
    assert client.get("/api/health").json()["auth"] == "api-key"


def test_labelled_outcomes_endpoint(client):
    client.post("/sim/advance", data={"minutes": 30, "next": "/app"})
    rows = client.get("/api/outcomes").json()["rows"]
    assert {r["order_id"] for r in rows} == {"SE-1042", "SE-1051"}
    assert all("order_result" in r for r in rows)


def test_unknown_page_renders_a_helpful_404(client):
    r = client.get("/exceptions/99999")
    assert r.status_code == 404
    assert "Back to the exception queue" in r.text
    assert client.get("/api/nope").status_code == 404


def test_open_redirect_blocked(client):
    for target in ("//evil.example", "https://evil.example", "/\\evil.example"):
        r = client.post("/role", data={"role": "coordinator", "next": target}, follow_redirects=False)
        assert r.headers["location"] == "/app", target


def test_vietnamese_interface(client):
    r = client.get("/app?lang=vi")
    assert "Hàng đợi ngoại lệ" in r.text
    # The choice is remembered.
    assert "Hàng đợi ngoại lệ" in client.get("/orders").text
    client.post("/sim/advance", data={"minutes": 30, "next": "/app"})
    assert "Chưa xác nhận lấy hàng" in client.get("/app").text
    xid = client.get("/api/exceptions").json()["open"][0]["id"]
    detail = client.get(f"/exceptions/{xid}").text
    assert "Chưa xác nhận lấy hàng trước 09:30; chuyến xuất lúc 10:00." in detail
    assert "Giao cho Anna Lind." in detail  # system audit note translated
    assert "Bảng điểm pilot" in client.get("/kpi").text
    assert "Exception queue" in client.get("/app?lang=en").text


def test_every_template_string_has_a_vietnamese_translation():
    from promiseops.web.i18n import VI

    missing = set()
    for f in (Path(__file__).resolve().parents[2] / "src/promiseops/web/templates").glob("*.html"):
        for s in re.findall(r"_\('([^']+)'", f.read_text(encoding="utf8")):
            if s not in VI:
                missing.add(s)
    assert not missing, sorted(missing)


def test_every_user_facing_error_has_a_vietnamese_translation():
    from promiseops.web.i18n import VI

    src = Path(__file__).resolve().parents[2] / "src/promiseops"
    messages = set()
    for f in [src / "core/workflow.py", src / "web/routes/actions.py", src / "web/routes/demo.py"]:
        messages |= set(re.findall(r'(?:ActionError|done|msg=)\(?\s*"([^"{]+)"', f.read_text(encoding="utf8")))
    messages |= {"Ownership taken", "Escalated to the shift lead", "Outcome recorded", "Note added"}
    missing = sorted(m for m in messages if m not in VI and not m.startswith("Clock moved"))
    assert not missing, missing


def test_feed_outage_shows_a_live_banner_and_a_data_task(client):
    client.post("/sim/advance", data={"minutes": 10, "next": "/app"})
    client.post("/sim/feed", data={"action": "pause", "next": "/app"})
    client.post("/sim/advance", data={"minutes": 45, "next": "/app"})
    html = client.get("/app").text
    assert "Fulfilment data is stale." in html
    assert "No fulfilment data for 45 min" in html
    assert "Integration desk" in client.get("/data").text


def test_heartbeat_keeps_a_quiet_feed_fresh(client):
    assert client.post("/api/sources/nope/heartbeat").status_code == 404
    r = client.post("/api/sources/wms/heartbeat")
    assert r.status_code == 200 and r.json()["outcome"] == "read recorded"
    wms = next(s for s in client.get("/api/health").json()["sources"] if s["id"] == "wms")
    assert wms["age"] == 0


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    from promiseops import clock
    from promiseops.web import app as main
    from promiseops.web import deps

    monkeypatch.setattr(clock, "DEMO", False)
    monkeypatch.setattr(deps.settings, "db_path", tmp_path / "pilot.db")
    monkeypatch.setattr(deps.settings, "api_key", None)
    with TestClient(main.app) as c:
        yield c


def test_pilot_mode_runs_on_the_wall_clock_without_demo_controls(pilot):
    from datetime import datetime, timedelta, timezone

    from promiseops.web import app as main

    health = pilot.get("/api/health").json()
    assert health["mode"] == "pilot"
    now = datetime.fromisoformat(health["now"])
    assert abs((datetime.now(timezone.utc) - now).total_seconds()) < 120
    assert pilot.post("/sim/advance", data={"minutes": 30}).status_code == 404
    assert pilot.post("/sim/reset").status_code == 404
    assert "Demo controls" not in pilot.get("/app").text

    # A real order whose pick was due 10 minutes ago, and a live but quiet warehouse feed.
    iso = lambda m: (now + timedelta(minutes=m)).isoformat()  # noqa: E731
    order = {"id": "SE-9001", "market": "SE", "dc": "DC Stockholm South", "store": "S01 Sodermalm",
             "customer_type": "B2B", "customer_ref": "Trade customer 9001", "pick_due_at": iso(-10),
             "dispatch_cutoff_at": iso(20), "latest_dispatch_at": iso(90), "promised_at": iso(240)}
    assert pilot.post("/api/orders", json=order).json()["outcome"] == "accepted"
    assert pilot.post("/api/sources/wms/heartbeat").status_code == 200
    open_ = pilot.get("/api/exceptions").json()["open"]
    assert [(x["order_id"], x["type"]) for x in open_] == [("SE-9001", "MISSING_PICK")]

    main.run_rules_once()  # what the scheduler does every minute
    assert len(pilot.get("/api/exceptions").json()["open"]) == 1


def test_pilot_database_is_never_wiped_by_a_demo_restart(pilot, monkeypatch):
    from promiseops import clock
    from promiseops.web import deps

    def order_count() -> int:
        c = deps.db.connect(deps.settings.db_path)
        try:
            return c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        finally:
            c.close()

    from datetime import datetime, timedelta

    now = datetime.fromisoformat(pilot.get("/api/health").json()["now"])
    iso = lambda m: (now + timedelta(minutes=m)).isoformat()  # noqa: E731
    order = {"id": "SE-9002", "market": "SE", "dc": "DC Stockholm South", "store": "S01 Sodermalm",
             "customer_type": "B2C", "customer_ref": "Household 9002", "pick_due_at": iso(30),
             "dispatch_cutoff_at": iso(60), "latest_dispatch_at": iso(120), "promised_at": iso(300)}
    assert pilot.post("/api/orders", json=order).json()["outcome"] == "accepted"

    monkeypatch.setattr(clock, "DEMO", False)
    deps.ensure_db()  # same mode: kept as is
    assert order_count() == 1

    monkeypatch.setattr(clock, "DEMO", True)  # someone restarts without PROMISEOPS_MODE=pilot
    with pytest.raises(RuntimeError, match="holds pilot data"):
        deps.ensure_db()
    assert order_count() == 1


def test_a_failing_scheduler_tick_is_logged_not_fatal(monkeypatch, caplog):
    from promiseops.web import app as main

    def boom():
        raise RuntimeError("database is locked")

    monkeypatch.setattr(main, "run_rules_once", boom)
    assert main.scheduled_tick() is False
    assert "Scheduled rules cycle failed" in caplog.text
