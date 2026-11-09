"""Shared web plumbing: settings, database connection, role, language, rendering and redirects."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from promiseops import timeutil as tu
from promiseops.config import (
    AVOIDED_COST_PER_LATE_EUR, DEFAULT_MARKET, MIN_SAMPLE_FOR_TARGET, RESOLUTION_SHORT, EXCEPTION_TYPES, HUMAN_RESOLUTIONS, MARKETS, RESOLUTION_ROLES, RESOLUTIONS, ROLES,
)
from promiseops.core import queries, workflow
from promiseops.integration import simulation
from promiseops.storage import db, seed
from promiseops.web import i18n

WEB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = WEB_DIR.parents[2]
CFG = MARKETS[DEFAULT_MARKET]


@dataclass
class Settings:
    db_path: Path
    api_key: str | None  # when set, /api/* except /api/health requires the X-API-Key header


settings = Settings(
    db_path=Path(os.environ.get("PROMISEOPS_DB", PROJECT_ROOT / "var" / "promiseops.db")),
    api_key=os.environ.get("PROMISEOPS_API_KEY") or None,
)


def ensure_db() -> None:
    """Create the database on first start; rebuild the demo when the schema has changed."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    try:
        db.init(conn)
        if not db.is_current(conn):
            seed.seed(conn)
    finally:
        conn.close()


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_role(request: Request) -> str:
    """Demo sign-in: the role comes from a cookie set by the role switch. The pilot uses company SSO."""
    role = request.cookies.get("role", "coordinator")
    return role if role in ROLES else "coordinator"


def get_lang(request: Request) -> str:
    return i18n.pick(request.query_params.get("lang") or request.cookies.get("lang"))


def safe_path(target: str | None, default: str = "/app") -> str:
    """Only same-site paths are allowed as redirect targets (no //host, no scheme)."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return default
    return target.split("?")[0].split("#")[0]


def back(path: str, *, msg: str | None = None, error: str | None = None) -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    if error:
        path += f"{sep}error={quote(error)}"
    elif msg:
        path += f"{sep}msg={quote(msg)}"
    return RedirectResponse(path, status_code=303)


templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.filters["local"] = lambda v, fmt="%H:%M": tu.local(v, CFG.tz, fmt)
templates.env.filters["mins"] = tu.fmt_minutes
templates.env.globals.update(
    EXCEPTION_TYPES=EXCEPTION_TYPES, RESOLUTIONS=RESOLUTIONS, ROLES=ROLES, CFG=CFG,
    HUMAN_RESOLUTIONS=HUMAN_RESOLUTIONS, RESOLUTION_ROLES=RESOLUTION_ROLES, AVOIDED_EUR=AVOIDED_COST_PER_LATE_EUR,
    RESOLUTION_SHORT=RESOLUTION_SHORT, MIN_SAMPLE=MIN_SAMPLE_FOR_TARGET,
)


def page(request: Request, template: str, ctx: dict, status_code: int = 200) -> HTMLResponse:
    """Render in the reader's language; a ?lang= choice is remembered in a cookie."""
    lang = get_lang(request)
    tr = lambda text, **kw: i18n.translate(text, lang, **kw)  # noqa: E731
    resp = templates.TemplateResponse(
        request, template, {**ctx, "_": tr, "lang": lang, "LANGS": i18n.LANGS}, status_code=status_code,
    )
    if request.query_params.get("lang") == lang:
        resp.set_cookie("lang", lang, httponly=True, samesite="lax", max_age=365 * 24 * 3600)
    return resp


def render(request: Request, conn: sqlite3.Connection, template: str, active: str, **ctx) -> HTMLResponse:
    """Render a page of the working app: adds the rail (clock, feeds, role) and the flash message."""
    now = simulation.now(conn)
    role = get_role(request)
    open_count, mine = queries.counts(conn, role)
    shell = {
        "now": now, "now_iso": tu.iso(now), "role": role, "actor": workflow.actor_name(role, CFG.code),
        "active": active, "freshness": queries.freshness(conn, now, CFG), "open_count": open_count, "mine": mine,
        "msg": request.query_params.get("msg"), "error": request.query_params.get("error"),
        "stale_task": queries.open_stale_task(conn), "day": i18n.day_label(now, CFG.tz, get_lang(request)),
        "action_minutes": simulation.ACTION_MINUTES,
    }
    return page(request, template, {**shell, **ctx})
