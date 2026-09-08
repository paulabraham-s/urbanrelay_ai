"""UrbanRelay AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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
        # send an initial full snapshot so the client can bootstrap the map
        import json

        await ws.send_text(json.dumps({"type": "snapshot", **sim.snapshot()}, default=str))
        while True:
            message = await ws.receive_text()
            # keepalive ping
            if message == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:  # noqa: BLE001
        await manager.disconnect(ws)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "ws": "/ws/sim",
    }