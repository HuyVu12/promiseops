"""Human actions on an exception. Every change is attributed and logged; nothing writes back to source systems."""

from __future__ import annotations

import math
import sqlite3
from datetime import datetime

from promiseops import timeutil as tu
from promiseops.config import MARKETS, RESOLUTION_ROLES, RESOLUTIONS, ROLES
from promiseops.core.engine import audit

MAX_ACTION_COST_EUR = 100_000


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


def resolve(
    conn: sqlite3.Connection, exception_id: int, role: str, resolution: str, note: str, now: datetime,
    cost_eur: float | None = None,
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
    conn.commit()
