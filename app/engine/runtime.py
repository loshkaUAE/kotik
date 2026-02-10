from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from app.config import settings
from app.data.market_data import BybitDataHub
from app.engine.liquidity import LiquidityEngine
from app.engine.signals import SignalEngine
from app.indicators.technical import TechnicalIndicators
from app.risk.manager import RiskManager


class TradingRuntime:
    def __init__(self) -> None:
        self.data = BybitDataHub()
        self.risk = RiskManager(settings.max_risk_per_trade)
        self.signals = SignalEngine(self.risk)

    async def start(self) -> None:
        await self.data.start()

    async def stop(self) -> None:
        await self.data.stop()

    async def state(self, symbol: str, timeframe: str, balance: float | None = None, risk_pct: float | None = None) -> dict[str, Any]:
        snap = self.data.snapshot(symbol)
        pack = TechnicalIndicators.calculate(snap.klines.get(timeframe, []))
        liq = LiquidityEngine.analyze(pack.frame, snap.orderbook, snap.trades)
        signal, plan = self.signals.evaluate(pack.frame, liq, balance or settings.default_balance, risk_pct)
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': snap.timestamp,
            'funding_rate': snap.funding_rate,
            'open_interest': snap.open_interest,
            'orderbook': snap.orderbook,
            'liquidity': asdict(liq),
            'indicators': pack.frame.tail(300).to_dict(orient='records') if not pack.frame.empty else [],
            'signal': self.signals.asdict(signal),
            'plan': asdict(plan) if plan else None,
        }

    async def stream(self, symbol: str, timeframe: str):
        while True:
            yield await self.state(symbol, timeframe)
            await asyncio.sleep(1)
