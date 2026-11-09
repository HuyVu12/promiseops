"""PromiseOps web application: one FastAPI service with server-rendered pages and a small JSON API.

Run: python -m uvicorn --app-dir src promiseops.web.app:app --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from promiseops.web.deps import WEB_DIR, ensure_db, page
from promiseops.web.routes import actions, api, demo, pages


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_db()
    yield


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
