import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Keeps track of all connected WebSocket clients and broadcasts messages."""

    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._clients.append(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self._clients))

    def disconnect(self, websocket: WebSocket):
        self._clients.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self._clients))

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for client in self._clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)
        for client in disconnected:
            self._clients.remove(client)


# Singleton — shared across the whole API process
manager = WebSocketManager()
