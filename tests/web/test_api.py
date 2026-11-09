"""HTTP-level checks: pages render, actions redirect with feedback, API validates input."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from promiseops.web import app as main

    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    with TestClient(main.app) as c:
        yield c


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
    r = client.post(f"/exceptions/{xid}/resolve", data={"resolution": "EXPEDITED", "note": "x"})
    assert "Escalate to the shift lead" in r.text

    client.post(f"/exceptions/{xid}/escalate", data={"note": "Not picked"})
    client.post("/role", data={"role": "shift_lead", "next": "/app"})
    r = client.post(f"/exceptions/{xid}/resolve", data={"resolution": "EXPEDITED", "note": "Priority pick"})
    assert "Saved" in r.text
    assert "Expedited by shift lead" in client.get(f"/exceptions/{xid}").text


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


def test_open_redirect_blocked(client):
    r = client.post("/role", data={"role": "coordinator", "next": "//evil.example"}, follow_redirects=False)
    assert r.headers["location"] == "/app"


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
    assert "Exception queue" in client.get("/app?lang=en").text


def test_every_template_string_has_a_vietnamese_translation():
    import re
    from pathlib import Path
    from promiseops.web.i18n import VI
    missing = set()
    for f in (Path(__file__).resolve().parents[2] / "src/promiseops/web/templates").glob("*.html"):
        for s in re.findall(r"_\('([^']+)'", f.read_text(encoding="utf8")):
            if s not in VI:
                missing.add(s)
    assert not missing, sorted(missing)
