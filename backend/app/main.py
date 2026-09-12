"""UrbanRelay AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    agents,
    alerts,
    analytics,
    auth,
    cities,
    curb,
    dashboard,
    dispatch,
    fleet,
    health,
    hubs,
    orders,
    routes,
    simulation,
)
from app.api.deps import get_sim_service
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.ws import manager
from app.database.session import SessionLocal, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.debug)
    init_db()

    # ensure demo users exist
    db = SessionLocal()
    try:
        from app.api.auth import seed_users

        seed_users(db)
    finally:
        db.close()

    # load topology + road graph + simulation engine
    sim = get_sim_service()
    sim.init()

    # auto-start the simulation so data is visible immediately
    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    loop.create_task(sim.start("FESTIVAL_SALE", 42, 3.0, burst=50))

    logger.info("UrbanRelay AI backend ready")
    yield


settings = get_settings()
app = FastAPI(
    title="UrbanRelay AI",
    description="India's Collaborative Smart Logistics Grid — AI city logistics orchestration platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    health.router,
    auth.router,
    cities.router,
    orders.router,
    hubs.router,
    fleet.router,
    curb.router,
    routes.router,
    simulation.router,
    dashboard.router,
    analytics.router,
    agents.router,
    alerts.router,
    dispatch.router,
):
    app.include_router(r)


@app.websocket("/ws/sim")
async def ws_sim(ws: WebSocket):
    await manager.connect(ws)
    sim = get_sim_service()
    try:
        import json
        await ws.send_text(json.dumps({"type": "snapshot", **sim.snapshot()}, default=str))
        while True:
            message = await ws.receive_text()
            if message == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:  # noqa: BLE001
        await manager.disconnect(ws)


# ── Serve frontend static files in production ──────────────────────────
_frontend_dist = Path(settings.frontend_dist)
if _frontend_dist.is_dir():
    # Serve real static assets (JS, CSS, images, GeoJSON data)
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")
    _data_dir = _frontend_dist / "data"
    if _data_dir.is_dir():
        app.mount("/data", StaticFiles(directory=str(_data_dir)), name="static-data")

    # SPA fallback: serve index.html for any 404 that isn't an API route
    _index_html = _frontend_dist / "index.html"
    _api_prefixes = ("/api/", "/health", "/ready", "/docs", "/ws/", "/openapi.json")

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        path = request.url.path
        # Let API / docs / WebSocket 404s return normally
        if path.startswith(_api_prefixes):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # For everything else, serve index.html (React Router handles client routing)
        return FileResponse(str(_index_html))