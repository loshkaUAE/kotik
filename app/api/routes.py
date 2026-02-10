from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.engine import TradingEngine

router = APIRouter()
engine = TradingEngine()


@router.get('/health')
async def health() -> dict:
    return {'status': 'ok'}


@router.get('/setups')
async def setups() -> dict:
    return await engine.tick()


@router.websocket('/ws/live')
async def ws_live(ws: WebSocket) -> None:
    await ws.accept()
    try:
        async for packet in engine.stream():
            await ws.send_text(json.dumps(packet, default=str))
    except WebSocketDisconnect:
        return
