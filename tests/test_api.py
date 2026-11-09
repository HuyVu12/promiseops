"""HTTP-level checks: pages render, actions redirect with feedback, API validates input."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    with TestClient(main.app) as c:
        yield c


def test_pages_render(client):
    for path in ["/", "/orders", "/kpi", "/data", "/?view=mine"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "PromiseOps" in r.text


def test_full_journey_over_http(client):
    client.post("/sim/advance", data={"minutes": 30, "next": "/"})
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
    client.post("/role", data={"role": "shift_lead", "next": "/"})
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
    assert r.headers["location"] == "/"
