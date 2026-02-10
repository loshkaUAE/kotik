from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionPlan:
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    rr: float
    risk_amount: float
    position_size: float


class RiskManager:
    def __init__(self, max_risk_per_trade: float) -> None:
        self.max_risk_per_trade = max_risk_per_trade

    def plan(self, *, balance: float, risk_pct: float | None, entry: float, atr: float, structure_stop: float) -> PositionPlan:
        risk_fraction = min(self.max_risk_per_trade, risk_pct if risk_pct is not None else self.max_risk_per_trade)
        stop_loss = min(structure_stop, entry - 1.2 * atr)
        risk_per_unit = max(1e-9, entry - stop_loss)
        risk_amount = balance * risk_fraction
        size = risk_amount / risk_per_unit
        tp1 = entry + 2 * risk_per_unit
        tp2 = entry + 3 * risk_per_unit
        tp3 = entry + 4 * risk_per_unit
        rr = (tp1 - entry) / risk_per_unit
        return PositionPlan(entry, stop_loss, tp1, tp2, tp3, rr, risk_amount, size)
