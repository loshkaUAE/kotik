from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    risk_amount: float
    position_size: float
    leverage: float
    liquidation_price: float


class RiskManager:
    def __init__(self, max_risk: float, max_trades_per_hour: int, blocked_funding_rate: float) -> None:
        self.max_risk = max_risk
        self.max_trades_per_hour = max_trades_per_hour
        self.blocked_funding_rate = blocked_funding_rate

    def evaluate(
        self,
        *,
        balance: float,
        entry: float,
        stop: float,
        funding_rate: float,
        trades_last_hour: int,
        revenge_score: float,
    ) -> RiskDecision:
        if abs(funding_rate) > self.blocked_funding_rate:
            return RiskDecision(False, 'blocked: funding rate too high', 0, 0, 0, 0)
        if trades_last_hour >= self.max_trades_per_hour:
            return RiskDecision(False, 'blocked: overtrading detected', 0, 0, 0, 0)
        if revenge_score > 0.75:
            return RiskDecision(False, 'blocked: revenge trading behavior', 0, 0, 0, 0)

        risk_amount = balance * self.max_risk
        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return RiskDecision(False, 'invalid stop distance', 0, 0, 0, 0)

        position_size = risk_amount / stop_distance
        leverage = max(1.0, min(20.0, (position_size * entry) / balance))
        liquidation = entry * (1 - (1 / leverage) * 0.8)

        return RiskDecision(True, 'ok', risk_amount, position_size, leverage, liquidation)
