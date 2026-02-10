from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.core.indicators import IndicatorsEngine
from app.core.liquidity import LiquidityAnalyzer
from app.core.market_data import BybitMarketDataClient
from app.core.risk import RiskManager
from app.core.signals import SignalEngine


class TradingEngine:
    def __init__(self) -> None:
        self.market = BybitMarketDataClient(settings.symbols)
        self.risk = RiskManager(settings.max_risk_per_trade, settings.max_trades_per_hour, settings.blocked_funding_rate)
        self.signals = SignalEngine(self.risk)
        self.active_setups: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        await self.market.start()

    async def tick(self) -> dict[str, Any]:
        payload: dict[str, Any] = {'timestamp': datetime.now(tz=timezone.utc).isoformat(), 'symbols': {}}
        for symbol in settings.symbols:
            snap = self.market.snapshot(symbol)
            ind = IndicatorsEngine.from_klines(snap.klines.get('1', []))
            liq = LiquidityAnalyzer.analyze(ind.frame, snap.orderbook, snap.trades)
            signal = self.signals.generate(
                symbol=symbol,
                indicators=ind.frame,
                liquidity=liq,
                funding_rate=snap.funding_rate or 0.0,
                balance=10_000,
                trades_last_hour=1,
                revenge_score=0.1,
            )
            snapshot = {
                'last_price': float(ind.frame['close'].iloc[-1]) if not ind.frame.empty else None,
                'funding_rate': snap.funding_rate,
                'open_interest': snap.open_interest,
                'indicators': ind.frame.tail(200).to_dict(orient='records') if not ind.frame.empty else [],
                'liquidity': asdict(liq),
                'signal': asdict(signal) if signal else None,
            }
            self.active_setups[symbol] = snapshot
            payload['symbols'][symbol] = snapshot
        return payload

    async def stream(self):
        while True:
            yield await self.tick()
            await asyncio.sleep(1)
