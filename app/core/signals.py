from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.config import settings
from app.core.liquidity import LiquidityState
from app.core.risk import RiskManager


@dataclass
class Signal:
    symbol: str
    side: str
    probability: float
    conditions_met: int
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    rr: float
    leverage: float
    risk_pct: float
    liquidation_price: float
    rationale: list[str]


class SignalEngine:
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def generate(
        self,
        *,
        symbol: str,
        indicators: pd.DataFrame,
        liquidity: LiquidityState,
        funding_rate: float,
        balance: float,
        trades_last_hour: int,
        revenge_score: float,
    ) -> Signal | None:
        if indicators.empty or len(indicators) < 60:
            return None
        last = indicators.iloc[-1]
        prev = indicators.iloc[-2]

        conditions: list[tuple[bool, str]] = [
            (last['ema_9'] > last['ema_21'], 'ema9 > ema21'),
            (last['ema_21'] > last['ema_50'], 'ema21 > ema50'),
            (last['close'] > last['ema_200'], 'price > ema200'),
            (last['macd'] > last['macd_signal'], 'macd bullish'),
            (50 < last['rsi'] < 70, 'rsi in trend zone'),
            (last['adx'] > 20, 'adx trend strength'),
            (last['close'] > last['vwap'], 'price > vwap'),
            (last['close'] > last['pivot'], 'price > pivot'),
            (last['close'] > prev['resistance'] * 0.995, 'near resistance break'),
            (liquidity.order_flow_imbalance > 0.05, 'positive order flow imbalance'),
            (liquidity.absorption_score > 0.2, 'orderbook absorption'),
            (len(liquidity.stop_hunts) > 0, 'stop hunt printed'),
            (len(liquidity.fvg_zones) > 0, 'fvg identified'),
            (last['hh'] and last['hl'], 'market structure hh/hl'),
            (last['cvd'] > indicators['cvd'].iloc[-20], 'cvd uptrend'),
        ]

        met = [d for ok, d in conditions if ok]
        n_met = len(met)
        score = n_met / len(conditions)
        if n_met < settings.min_conditions_for_signal or score < settings.signal_probability_threshold:
            return None

        entry = float(last['close'])
        atr = float(last['atr']) if not np.isnan(last['atr']) else entry * 0.003
        stop = float(min(last['support'], entry - 1.2 * atr))
        risk = entry - stop
        tp1 = entry + risk * 2
        tp2 = entry + risk * 3
        tp3 = entry + risk * 4
        rr = (tp1 - entry) / max(1e-9, (entry - stop))
        if rr < 2:
            return None

        decision = self.risk_manager.evaluate(
            balance=balance,
            entry=entry,
            stop=stop,
            funding_rate=funding_rate,
            trades_last_hour=trades_last_hour,
            revenge_score=revenge_score,
        )
        if not decision.allowed:
            return None

        return Signal(
            symbol=symbol,
            side='long',
            probability=score,
            conditions_met=n_met,
            entry=entry,
            stop_loss=stop,
            tp1=float(tp1),
            tp2=float(tp2),
            tp3=float(tp3),
            rr=float(rr),
            leverage=decision.leverage,
            risk_pct=settings.max_risk_per_trade,
            liquidation_price=decision.liquidation_price,
            rationale=met,
        )
