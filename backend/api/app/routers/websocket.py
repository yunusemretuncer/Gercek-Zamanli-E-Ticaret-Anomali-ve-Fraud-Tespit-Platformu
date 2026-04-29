import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep connection alive — wait for client to disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
