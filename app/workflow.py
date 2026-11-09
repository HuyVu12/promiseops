"""Human actions on an exception. Every change is attributed and logged; nothing writes back to source systems."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from . import timeutil as tu
from .config import MARKETS, RESOLUTION_ROLES, RESOLUTIONS, ROLES
from .engine import audit


class ActionError(ValueError):
    pass


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
    if x["status"] == "RESOLVED":
        raise ActionError("Exception is already resolved")
    if x["owner_role"] == "shift_lead":
        raise ActionError("Already with the shift lead")
    note = note.strip()
    if not note:
        raise ActionError("Say what the shift lead needs to decide")
    cfg = MARKETS[x["market"]]
    actor = actor_name(role, x["market"])
    conn.execute(
        "UPDATE exceptions SET escalated = 1, owner = ?, owner_role = 'shift_lead' WHERE id = ?",
        (cfg.shift_lead, exception_id),
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


def resolve(conn: sqlite3.Connection, exception_id: int, role: str, resolution: str, note: str, now: datetime) -> None:
    _check_role(role)
    x = _load(conn, exception_id)
    if x["status"] == "RESOLVED":
        raise ActionError("Exception is already resolved")
    if resolution not in RESOLUTION_ROLES:
        raise ActionError("Unknown outcome")
    if role not in RESOLUTION_ROLES[resolution]:
        raise ActionError(f"{ROLES[role]} cannot record '{RESOLUTIONS[resolution]}'. Escalate to the shift lead.")
    note = note.strip()
    if not note:
        raise ActionError("Record what you verified and why")
    actor = actor_name(role, x["market"])
    if x["status"] == "OPEN":
        # Resolving implies ownership; keep the acknowledgement time honest.
        conn.execute(
            "UPDATE exceptions SET acknowledged_at = ? WHERE id = ? AND acknowledged_at IS NULL",
            (tu.iso(now), exception_id),
        )
    conn.execute(
        "UPDATE exceptions SET status = 'RESOLVED', resolution = ?, resolved_at = ?, owner = ?, owner_role = ? WHERE id = ?",
        (resolution, tu.iso(now), actor, role, exception_id),
    )
    audit(conn, exception_id, now, actor, resolution, note)
    conn.commit()
