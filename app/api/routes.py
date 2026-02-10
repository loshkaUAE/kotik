from __future__ import annotations

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.config import settings
from app.engine.runtime import TradingRuntime

router = APIRouter()
runtime = TradingRuntime()


class RecommendationRequest(BaseModel):
    symbol: str
    timeframe: str = '1'
    entry: float
    balance: float = settings.default_balance
    risk_pct: float = settings.max_risk_per_trade


@router.get('/health')
async def health() -> dict:
    return {'status': 'ok'}


@router.get('/state')
async def state(symbol: str = Query('BTCUSDT'), timeframe: str = Query('1')) -> dict:
    return await runtime.state(symbol, timeframe)


@router.post('/recommendation')
async def recommendation(payload: RecommendationRequest) -> dict:
    st = await runtime.state(payload.symbol, payload.timeframe, payload.balance, payload.risk_pct)
    indicators = st.get('indicators', [])
    if not indicators:
        return {'error': 'Not enough market data'}
    last = indicators[-1]
    atr = float(last.get('atr') or payload.entry * 0.004)
    support = float(last.get('support') or payload.entry - atr)
    from app.risk.manager import RiskManager

    plan = RiskManager(settings.max_risk_per_trade).plan(
        balance=payload.balance,
        risk_pct=payload.risk_pct,
        entry=payload.entry,
        atr=atr,
        structure_stop=support,
    )
    prob = st.get('signal', {}).get('probability', 0.0) if st.get('signal') else 0.0
    return {
        'entry': payload.entry,
        'recommended_stop_loss': plan.stop_loss,
        'recommended_tp1': plan.tp1,
        'recommended_tp2': plan.tp2,
        'recommended_tp3': plan.tp3,
        'risk_reward': plan.rr,
        'probability_score': prob,
    }


@router.websocket('/ws/live')
async def ws_live(
    ws: WebSocket,
    symbol: str = Query('BTCUSDT'),
    timeframe: str = Query('1'),
) -> None:
    await ws.accept()
    try:
        async for packet in runtime.stream(symbol, timeframe):
            await ws.send_text(json.dumps(packet, default=str))
    except WebSocketDisconnect:
        return
