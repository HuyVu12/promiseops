"""Behaviour of the rules, workflow and measurement on the fictional SE-1042 morning."""

import pytest

from app import engine, ingest, kpi, simulation, workflow
from app import timeutil as tu
from app.seed import DAY, TZ


def at(hhmm):
    return tu.local_dt(DAY, hhmm, TZ)


def exc(conn, order_id, type_):
    return conn.execute("SELECT * FROM exceptions WHERE order_id = ? AND type = ?", (order_id, type_)).fetchone()


def advance_to(conn, hhmm):
    minutes = tu.minutes_between(simulation.now(conn), at(hhmm))
    if minutes > 0:
        simulation.advance(conn, minutes)


def delivered(conn, order_id):
    row = conn.execute(
        "SELECT MIN(occurred_at) AS t FROM events WHERE order_id = ? AND type = 'DELIVERED'", (order_id,)
    ).fetchone()
    return row["t"]


def test_no_alerts_before_any_milestone(conn):
    assert conn.execute("SELECT COUNT(*) AS n FROM exceptions").fetchone()["n"] == 0


def test_missing_pick_raised_at_pick_due_with_dispatch_deadline(conn):
    advance_to(conn, "09:25")
    assert exc(conn, "SE-1042", "MISSING_PICK") is None
    advance_to(conn, "09:30")
    x = exc(conn, "SE-1042", "MISSING_PICK")
    assert x["status"] == "OPEN"
    assert x["owner"] == "Anna Lind"
    assert x["intervention_deadline"] == tu.iso(at("10:00"))
    assert x["ack_due_at"] == tu.iso(at("09:45"))
    # On-time orders on the same route raise nothing.
    assert exc(conn, "SE-1031", "MISSING_PICK") is None


def test_unacknowledged_alert_escalates_to_shift_lead(conn):
    advance_to(conn, "10:00")
    assert exc(conn, "SE-1060", "MISSING_PICK")["escalated"] == 0
    advance_to(conn, "10:20")
    x = exc(conn, "SE-1060", "MISSING_PICK")
    assert x["escalated"] == 1
    assert x["owner"] == "Erik Berg"
    assert x["owner_role"] == "shift_lead"


def test_late_event_auto_clears_untouched_alert(conn):
    advance_to(conn, "10:25")
    x = exc(conn, "SE-1060", "MISSING_PICK")
    assert x["status"] == "RESOLVED"
    assert x["resolution"] == "AUTO_CLEARED"


def test_late_event_on_worked_alert_only_informs_owner(conn):
    advance_to(conn, "09:30")
    x = exc(conn, "SE-1051", "MISSING_PICK")
    workflow.acknowledge(conn, x["id"], "coordinator", at("09:30"))
    advance_to(conn, "09:55")
    x = exc(conn, "SE-1051", "MISSING_PICK")
    assert x["status"] == "ACKNOWLEDGED"
    actions = [r["action"] for r in conn.execute("SELECT action FROM audit_log WHERE exception_id = ?", (x["id"],))]
    assert "EVENT_ARRIVED" in actions


def test_one_exception_per_order_and_cause(conn):
    advance_to(conn, "11:00")
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM exceptions WHERE order_id = 'SE-1042' AND type = 'MISSING_PICK'"
    ).fetchone()["n"]
    assert n == 1
    # Still unpicked after the cutoff: no second dispatch alert for the same root cause.
    assert exc(conn, "SE-1042", "MISSING_DISPATCH") is None


def test_coordinator_cannot_expedite(conn):
    advance_to(conn, "09:30")
    x = exc(conn, "SE-1042", "MISSING_PICK")
    with pytest.raises(workflow.ActionError, match="Escalate"):
        workflow.resolve(conn, x["id"], "coordinator", "EXPEDITED", "please", at("09:30"))


def test_resolution_requires_evidence(conn):
    advance_to(conn, "09:30")
    x = exc(conn, "SE-1051", "MISSING_PICK")
    with pytest.raises(workflow.ActionError):
        workflow.resolve(conn, x["id"], "coordinator", "FALSE_ALARM", "   ", at("09:30"))


def test_expedite_in_time_keeps_original_promise(conn):
    advance_to(conn, "09:30")
    x = exc(conn, "SE-1042", "MISSING_PICK")
    workflow.acknowledge(conn, x["id"], "coordinator", at("09:30"))
    workflow.escalate(conn, x["id"], "coordinator", "Not picked, need a priority pick", at("09:35"))
    workflow.resolve(conn, x["id"], "shift_lead", "EXPEDITED", "Priority pick, picker moved", at("09:40"))
    advance_to(conn, "16:00")
    assert delivered(conn, "SE-1042") <= tu.iso(at("14:00"))
    # Expedited order is re-planned to the last viable dispatch, so no duplicate dispatch alert.
    assert exc(conn, "SE-1042", "MISSING_DISPATCH") is None


def test_without_action_order_is_late_and_counted_late(conn):
    advance_to(conn, "16:00")
    assert delivered(conn, "SE-1042") > tu.iso(at("14:00"))
    k = kpi.compute(conn, simulation.now(conn))
    assert k["segments"]["All"]["delivered"] == 16
    # SE-1042 and SE-1077 miss the promise when nobody acts.
    assert k["segments"]["All"]["late"] == 2


def test_promise_is_immutable_on_resend(conn):
    now = simulation.now(conn)
    original = conn.execute("SELECT promised_at FROM orders WHERE id = 'SE-1042'").fetchone()["promised_at"]
    order = dict(conn.execute("SELECT * FROM orders WHERE id = 'SE-1042'").fetchone())
    order["promised_at"] = tu.iso(at("18:00"))
    result = ingest.ingest_order(conn, order, now)
    assert result.outcome == "duplicate"
    assert conn.execute("SELECT promised_at FROM orders WHERE id = 'SE-1042'").fetchone()["promised_at"] == original


def test_duplicate_and_invalid_events(conn):
    now = simulation.now(conn)
    args = dict(source="wms", event_id="X-1", order_id="SE-1042", type="PICK_CONFIRMED", occurred_at=tu.iso(now))
    assert ingest.ingest_event(conn, now=now, **args).outcome == "accepted"
    assert ingest.ingest_event(conn, now=now, **args).outcome == "duplicate"
    bad = {**args, "event_id": "X-2", "order_id": "NOPE"}
    assert ingest.ingest_event(conn, now=now, **bad).detail == "unknown order"
    future = {**args, "event_id": "X-3", "occurred_at": tu.iso(at("12:00"))}
    assert ingest.ingest_event(conn, now=now, **future).detail == "timestamp is in the future"
    naive = {**args, "event_id": "X-4", "occurred_at": "2026-11-10T09:00:00"}
    assert ingest.ingest_event(conn, now=now, **naive).outcome == "rejected"


def test_stale_feed_pauses_absence_alerts_then_recovers(conn):
    advance_to(conn, "09:20")
    simulation.set_paused(conn, "wms", True)
    advance_to(conn, "09:45")
    # Feed last read at 09:20, before SE-1042's 09:30 milestone: silence proves nothing yet.
    assert exc(conn, "SE-1042", "MISSING_PICK") is None
    assert conn.execute("SELECT * FROM data_tasks").fetchone() is None  # 25 min: not stale yet
    advance_to(conn, "10:00")
    # Exactly 30 min old is still inside the limit, but the feed was last read at 09:20, before the
    # 10:00 milestone, so orders picked during the outage must not raise false alarms.
    for oid in ("SE-1039", "SE-1044", "SE-1047", "SE-1060"):
        assert exc(conn, oid, "MISSING_PICK") is None, oid
    assert exc(conn, "SE-1031", "MISSING_DISPATCH") is None
    advance_to(conn, "10:05")
    task = conn.execute("SELECT * FROM data_tasks WHERE closed_at IS NULL").fetchone()
    assert task is not None
    # SE-1060 pick due 10:00 but data is stale: no alert from missing data.
    assert exc(conn, "SE-1060", "MISSING_PICK") is None
    simulation.set_paused(conn, "wms", False)
    advance_to(conn, "10:10")
    assert conn.execute("SELECT * FROM data_tasks WHERE closed_at IS NULL").fetchone() is None
    # Backlog arrives first, then rules run on fresh data: SE-1060 is genuinely unpicked.
    assert exc(conn, "SE-1060", "MISSING_PICK") is not None
    assert exc(conn, "SE-1042", "MISSING_PICK") is not None
    # Orders handled during the outage stay quiet after recovery.
    for oid in ("SE-1039", "SE-1044", "SE-1047"):
        assert exc(conn, oid, "MISSING_PICK") is None, oid


def test_kpi_after_full_worked_morning(conn):
    advance_to(conn, "09:30")
    a = exc(conn, "SE-1051", "MISSING_PICK")
    workflow.acknowledge(conn, a["id"], "coordinator", at("09:30"))
    workflow.resolve(conn, a["id"], "coordinator", "FALSE_ALARM", "Picker confirms tote packed 09:20", at("09:35"))
    b = exc(conn, "SE-1042", "MISSING_PICK")
    workflow.acknowledge(conn, b["id"], "coordinator", at("09:35"))
    workflow.resolve(conn, b["id"], "shift_lead", "EXPEDITED", "Priority pick", at("09:40"))
    advance_to(conn, "16:00")
    k = kpi.compute(conn, simulation.now(conn))
    assert k["segments"]["All"]["late"] == 1  # only SE-1077, no vehicle
    assert k["by_resolution"]["FALSE_ALARM"] == 1
    assert k["by_resolution"]["EXPEDITED"] == 1
    # SE-1060 (late pick) and SE-1077 (vehicle came at 11:50, nobody worked it) cleared on their own.
    assert k["by_resolution"]["AUTO_CLEARED"] == 2
    assert exc(conn, "SE-1077", "MISSING_DISPATCH")["resolution"] == "AUTO_CLEARED"
    assert k["segments"]["B2B"]["delivered"] + k["segments"]["B2C"]["delivered"] == 16
