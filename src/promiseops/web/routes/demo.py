"""Demo harness controls. Simulation only: they replace real OMS/WMS feeds and wall-clock time."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form

from promiseops import timeutil as tu
from promiseops.config import FULFILMENT_SOURCE
from promiseops.integration import simulation
from promiseops.storage import seed
from promiseops.web.deps import CFG, back, get_conn, safe_path

router = APIRouter(prefix="/sim")


@router.post("/advance")
def advance(minutes: int = Form(...), next: str = Form("/app"), conn: sqlite3.Connection = Depends(get_conn)):
    try:
        t = simulation.advance(conn, minutes)
    except ValueError as exc:
        return back(safe_path(next), error=str(exc))
    return back(safe_path(next), msg=f"Clock moved to {tu.local(t, CFG.tz)}")


@router.post("/feed")
def feed(action: str = Form(...), next: str = Form("/app"), conn: sqlite3.Connection = Depends(get_conn)):
    pause = action == "pause"
    simulation.set_paused(conn, FULFILMENT_SOURCE, pause)
    return back(safe_path(next), msg="Fulfilment feed paused" if pause else "Fulfilment feed resumed")


@router.post("/reset")
def reset(conn: sqlite3.Connection = Depends(get_conn)):
    seed.seed(conn)
    return back("/app", msg="Scenario reset to 09:00")
