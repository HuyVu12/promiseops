"""PromiseOps web application: one FastAPI service with server-rendered pages and a small JSON API.

Run: python -m uvicorn --app-dir src promiseops.web.app:app --port 8000
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from promiseops import clock
from promiseops.core import engine
from promiseops.storage import db
from promiseops.web.deps import WEB_DIR, ensure_db, page, settings
from promiseops.web.routes import actions, api, demo, pages


def run_rules_once() -> None:
    """One scheduled rules cycle on the wall clock (pilot mode)."""
    conn = db.connect(settings.db_path)
    try:
        engine.run(conn, clock.now(conn))
    finally:
        conn.close()


async def _scheduler() -> None:
    # Pilot mode: response timers, escalation and the stale-feed guard must fire even when no record
    # arrives. In demo mode the harness runs the rules whenever the presenter moves the clock.
    while True:
        await asyncio.to_thread(run_rules_once)
        await asyncio.sleep(clock.RULES_EVERY_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_db()
    task = None if clock.DEMO else asyncio.create_task(_scheduler())
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    app = FastAPI(title="PromiseOps", version="1.0.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    for module in (pages, actions, demo, api):
        app.include_router(module.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/") or request.url.path.startswith("/static/"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
        return page(request, "error.html", {"status": exc.status_code, "detail": exc.detail}, exc.status_code)

    return app


app = create_app()
