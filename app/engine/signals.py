from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from app.config import settings
from app.engine.liquidity import LiquidityMap
from app.risk.manager import PositionPlan, RiskManager


@dataclass
class Signal:
    side: str
    probability: float
    confidence: float
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    rr: float
    explanation: list[str]


class SignalEngine:
    def __init__(self, risk_manager: RiskManager) -> None:
        self.risk = risk_manager

    def evaluate(self, frame: pd.DataFrame, liq: LiquidityMap, balance: float, risk_pct: float | None = None) -> tuple[Signal | None, PositionPlan | None]:
        if frame.empty or len(frame) < 80:
            return None, None
        l = frame.iloc[-1]
        p = frame.iloc[-2]
        conditions = [
            (l['ema_9'] > l['ema_21'], 'EMA9 > EMA21'),
            (l['ema_21'] > l['ema_50'], 'EMA21 > EMA50'),
            (l['close'] > l['ema_200'], 'Above EMA200'),
            (l['close'] > l['sma_20'], 'Above SMA20'),
            (l['macd'] > l['macd_signal'], 'MACD bullish'),
            (50 <= l['rsi'] <= 72, 'RSI trend zone'),
            (l['stoch_k'] > l['stoch_d'], 'Stochastic bullish crossover'),
            (l['adx'] > 20, 'ADX trending'),
            (l['close'] > l['vwap'], 'Above VWAP'),
            (l['close'] > l['pivot'], 'Above pivot'),
            (l['cvd'] > frame['cvd'].iloc[-20], 'CVD expansion'),
            (l['hh'] and l['hl'], 'HH/HL market structure'),
            (liq.order_flow_imbalance > 0.05, 'Positive order-flow imbalance'),
            (len(liq.fvg_zones) > 0, 'FVG present'),
            (len(liq.stop_hunts) > 0, 'Stop-hunt signal'),
            (bool(l['doji'] or l['hammer'] or l['bullish_engulfing']), 'Reversal/continuation candle pattern'),
        ]
        met = [desc for ok, desc in conditions if ok]
        prob = len(met) / len(conditions)
        if len(met) < settings.min_conditions_for_signal or prob < settings.signal_probability_threshold:
            return None, None

        entry = float(l['close'])
        atr = float(l['atr']) if pd.notna(l['atr']) else entry * 0.004
        structure_stop = float(min(l['support'], p['low']))
        plan = self.risk.plan(balance=balance, risk_pct=risk_pct, entry=entry, atr=atr, structure_stop=structure_stop)
        if plan.rr < 2:
            return None, None

        signal = Signal(
            side='long',
            probability=float(prob),
            confidence=float(prob),
            entry=plan.entry,
            stop_loss=plan.stop_loss,
            tp1=plan.tp1,
            tp2=plan.tp2,
            tp3=plan.tp3,
            rr=plan.rr,
            explanation=met,
        )
        return signal, plan

    @staticmethod
    def asdict(signal: Signal | None) -> dict[str, Any] | None:
        return asdict(signal) if signal else None
