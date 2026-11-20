"""Human actions on an exception. Every change is attributed and logged; nothing writes back to source systems."""

from __future__ import annotations

import math
import re
import sqlite3
from datetime import datetime

from promiseops import timeutil as tu
from promiseops.config import MARKETS, RESOLUTION_ROLES, RESOLUTIONS, ROLES
from promiseops.core.engine import SYSTEM, audit

MAX_ACTION_COST_EUR = 100_000

# A reference to the customer-service case, never the case itself: the conversation stays in the service
# team's own system (Salesforce in Denmark after the Round 3 migration). No CRM integration is needed.
CASE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./-]{0,39}$")

# Audit actions with a meaning outside the log: shadow decisions are never claimed as prevented lateness.
SHADOW_ACTION = "SHADOW_MODE"
SHADOW_NOTE = "Shadow pilot: recorded, not executed by PromiseOps. The live decision stays with the current floor process."
HANDOFF_ACTION = "HANDED_OVER"


class ActionError(ValueError):
    """A human action that the rules do not allow. The message is shown to the user."""


def actor_name(role: str, market: str = "SE") -> str:
    cfg = MARKETS[market]
    return {"coordinator": cfg.coordinator, "shift_lead": cfg.shift_lead}[role]


def _load(conn: sqlite3.Connection, exception_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT x.*, o.market FROM exceptions x JOIN orders o ON o.id = x.order_id WHERE x.id = ?", (exception_id,)
    ).fetchone()
    if not row:
        raise ActionError("Exception not found")
    return row


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise ActionError("Unknown role")


def _open_only(x: sqlite3.Row) -> None:
    if x["status"] == "RESOLVED":
        raise ActionError("Exception is already resolved")


def parse_cost(raw: str | float | None) -> float | None:
    """Optional euro amount from a form field; blank means not given."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        value = float(str(raw).replace(",", ".").replace("€", "").strip())
    except ValueError:
        raise ActionError("Intervention cost must be a number in euro") from None
    if math.isnan(value) or value < 0 or value > MAX_ACTION_COST_EUR:
        raise ActionError("Intervention cost must be between 0 and 100000 euro")
    return round(value, 2)


def acknowledge(conn: sqlite3.Connection, exception_id: int, role: str, now: datetime) -> None:
    _check_role(role)
    x = _load(conn, exception_id)
    if x["status"] != "OPEN":
        raise ActionError("Only open exceptions can be acknowledged")
    actor = actor_name(role, x["market"])
    conn.execute(
        "UPDATE exceptions SET status = 'ACKNOWLEDGED', acknowledged_at = ?, owner = ?, owner_role = ? WHERE id = ?",
        (tu.iso(now), actor, role, exception_id),
    )
    waited = tu.minutes_between(tu.parse(x["created_at"]), now)
    audit(conn, exception_id, now, actor, "ACKNOWLEDGED", f"Took ownership {waited} min after the alert.")
    conn.commit()


def escalate(conn: sqlite3.Connection, exception_id: int, role: str, note: str, now: datetime) -> None:
    _check_role(role)
    x = _load(conn, exception_id)
    _open_only(x)
    if x["owner_role"] == "shift_lead":
        raise ActionError("Already with the shift lead")
    note = note.strip()
    if not note:
        raise ActionError("Say what the shift lead needs to decide")
    cfg = MARKETS[x["market"]]
    actor = actor_name(role, x["market"])
    # Escalating is work on the case: it counts as ownership, so a late event no longer auto-clears it.
    conn.execute(
        "UPDATE exceptions SET escalated = 1, owner = ?, owner_role = 'shift_lead', status = 'ACKNOWLEDGED', "
        "acknowledged_at = COALESCE(acknowledged_at, ?) WHERE id = ?",
        (cfg.shift_lead, tu.iso(now), exception_id),
    )
    audit(conn, exception_id, now, actor, "ESCALATED", note)
    conn.commit()


def add_note(conn: sqlite3.Connection, exception_id: int, role: str, note: str, now: datetime) -> None:
    _check_role(role)
    x = _load(conn, exception_id)
    note = note.strip()
    if not note:
        raise ActionError("Note is empty")
    audit(conn, exception_id, now, actor_name(role, x["market"]), "NOTE", note)
    conn.commit()


def parse_case_ref(raw: str | None) -> str | None:
    """Optional customer-service case reference from a form field; blank means not given."""
    ref = (raw or "").strip()
    if not ref:
        return None
    if not CASE_REF.match(ref):
        raise ActionError("Case reference: up to 40 letters, digits, spaces or - _ . /")
    return ref


def resolve(
    conn: sqlite3.Connection, exception_id: int, role: str, resolution: str, note: str, now: datetime,
    cost_eur: float | None = None, case_ref: str | None = None, shadow: bool = False,
) -> None:
    _check_role(role)
    x = _load(conn, exception_id)
    _open_only(x)
    if resolution not in RESOLUTION_ROLES:
        raise ActionError("Choose what you verified")
    if role not in RESOLUTION_ROLES[resolution]:
        raise ActionError(f"{ROLES[role]} cannot record '{RESOLUTIONS[resolution]}'. Escalate to the shift lead.")
    note = note.strip()
    if not note:
        raise ActionError("Record what you verified and why")
    if resolution == "EXPEDITED" and cost_eur is None:
        raise ActionError("Log the intervention cost of the expedite (0 if none)")
    if case_ref and resolution != "CUSTOMER_NOTIFIED":
        raise ActionError("A case reference only goes with a handoff to customer service")
    actor = actor_name(role, x["market"])
    # Resolving implies ownership; keep the acknowledgement time honest.
    conn.execute(
        "UPDATE exceptions SET status = 'RESOLVED', resolution = ?, resolved_at = ?, owner = ?, owner_role = ?, "
        "action_cost_eur = ?, acknowledged_at = COALESCE(acknowledged_at, ?) WHERE id = ?",
        (resolution, tu.iso(now), actor, role, cost_eur, tu.iso(now), exception_id),
    )
    audit(conn, exception_id, now, actor, resolution, note)
    if cost_eur is not None:
        audit(conn, exception_id, now, actor, "COST_LOGGED", f"Intervention cost logged: EUR {cost_eur:g}.")
    if case_ref:
        audit(conn, exception_id, now, actor, HANDOFF_ACTION, f"Customer service case reference: {case_ref}.")
    if shadow:
        audit(conn, exception_id, now, SYSTEM, SHADOW_ACTION, SHADOW_NOTE)
    conn.commit()


def shadow_exception_ids(conn: sqlite3.Connection) -> set[int]:
    """Exceptions decided during a shadow pilot: the decision was recorded, not executed."""
    rows = conn.execute("SELECT DISTINCT exception_id FROM audit_log WHERE action = ?", (SHADOW_ACTION,))
    return {r["exception_id"] for r in rows}
