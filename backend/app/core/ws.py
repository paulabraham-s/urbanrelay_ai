"""WebSocket connection manager for real-time simulation broadcasts."""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.active.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self.active:
            return
        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        async with self._lock:
            sockets = list(self.active)
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()