"""Demo harness controls. Simulation only: they replace real OMS/WMS feeds and wall-clock time."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException

from promiseops import clock
from promiseops import timeutil as tu
from promiseops.config import FULFILMENT_SOURCE
from promiseops.integration import simulation
from promiseops.storage import seed
from promiseops.web.deps import CFG, back, get_conn, safe_path

def demo_only() -> None:
    """In pilot mode the demo controls do not exist: nobody can move the clock or reset the data."""
    if not clock.DEMO:
        raise HTTPException(404, "Not found")


router = APIRouter(prefix="/sim", dependencies=[Depends(demo_only)])


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
