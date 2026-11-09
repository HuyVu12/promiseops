"""Human actions on an exception (HTML forms). Each one is attributed, logged, and takes simulated time."""

from __future__ import annotations

import sqlite3
from typing import Callable

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from promiseops.config import ROLES
from promiseops import clock
from promiseops.core import workflow
from promiseops.integration import simulation
from promiseops.web.deps import back, get_conn, get_role, safe_path

router = APIRouter()


def _act(conn: sqlite3.Connection, exception_id: int, done: str, fn: Callable[[], None]) -> RedirectResponse:
    path = f"/exceptions/{exception_id}"
    try:
        fn()
    except workflow.ActionError as exc:
        return back(path, error=str(exc))
    if clock.DEMO:
        simulation.after_human_action(conn)  # demo: the action takes one simulated minute
    return back(path, msg=done)


@router.post("/exceptions/{exception_id}/ack")
def take_ownership(request: Request, exception_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return _act(conn, exception_id, "Ownership taken",
                lambda: workflow.acknowledge(conn, exception_id, get_role(request), now))


@router.post("/exceptions/{exception_id}/escalate")
def escalate(request: Request, exception_id: int, note: str = Form(""), conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return _act(conn, exception_id, "Escalated to the shift lead",
                lambda: workflow.escalate(conn, exception_id, get_role(request), note, now))


@router.post("/exceptions/{exception_id}/note")
def add_note(request: Request, exception_id: int, note: str = Form(""), conn: sqlite3.Connection = Depends(get_conn)):
    now = clock.now(conn)
    return _act(conn, exception_id, "Note added",
                lambda: workflow.add_note(conn, exception_id, get_role(request), note, now))


@router.post("/exceptions/{exception_id}/resolve")
def resolve(
    request: Request, exception_id: int, resolution: str = Form(""), note: str = Form(""), cost: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
):
    now = clock.now(conn)

    def record() -> None:
        workflow.resolve(conn, exception_id, get_role(request), resolution, note, now,
                         cost_eur=workflow.parse_cost(cost))

    return _act(conn, exception_id, "Outcome recorded", record)


@router.post("/role")
def switch_role(role: str = Form(...), next: str = Form("/app")):
    """Demo sign-in switch between the two roles of the MVP."""
    if role not in ROLES:
        raise HTTPException(400, "Unknown role")
    resp = RedirectResponse(safe_path(next), status_code=303)
    resp.set_cookie("role", role, httponly=True, samesite="lax")
    return resp

