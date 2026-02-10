from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class LiquidityState:
    buy_side_pools: list[float]
    sell_side_pools: list[float]
    sweeps: list[dict[str, Any]]
    stop_hunts: list[dict[str, Any]]
    imbalances: list[dict[str, Any]]
    fvg_zones: list[dict[str, Any]]
    absorption_score: float
    iceberg_score: float
    order_flow_imbalance: float
    delta_divergence: float


class LiquidityAnalyzer:
    @staticmethod
    def analyze(indicators: pd.DataFrame, orderbook: dict[str, Any], trades: list[dict[str, Any]]) -> LiquidityState:
        if indicators.empty:
            return LiquidityState([], [], [], [], [], [], 0.0, 0.0, 0.0, 0.0)

        highs = indicators['high'].tail(80)
        lows = indicators['low'].tail(80)
        buy_side = list(highs.nlargest(5).round(2))
        sell_side = list(lows.nsmallest(5).round(2))

        sweeps = []
        stop_hunts = []
        fvg_zones = []
        imbalances = []

        recent = indicators.tail(10)
        for i in range(2, len(recent)):
            prev2 = recent.iloc[i - 2]
            cur = recent.iloc[i]
            if cur['low'] > prev2['high']:
                fvg_zones.append({'type': 'bullish', 'low': float(prev2['high']), 'high': float(cur['low'])})
            if cur['high'] < prev2['low']:
                fvg_zones.append({'type': 'bearish', 'low': float(cur['high']), 'high': float(prev2['low'])})

            if cur['high'] > recent.iloc[i - 1]['high'] and cur['close'] < recent.iloc[i - 1]['high']:
                stop_hunts.append({'side': 'buy', 'level': float(recent.iloc[i - 1]['high'])})
            if cur['low'] < recent.iloc[i - 1]['low'] and cur['close'] > recent.iloc[i - 1]['low']:
                stop_hunts.append({'side': 'sell', 'level': float(recent.iloc[i - 1]['low'])})

        bids = orderbook.get('b', []) if isinstance(orderbook, dict) else []
        asks = orderbook.get('a', []) if isinstance(orderbook, dict) else []
        bid_volume = float(np.sum([float(x[1]) for x in bids[:50]])) if bids else 0.0
        ask_volume = float(np.sum([float(x[1]) for x in asks[:50]])) if asks else 0.0
        ofi = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) else 0.0

        if abs(ofi) > 0.2:
            imbalances.append({'ofi': ofi, 'bid_volume': bid_volume, 'ask_volume': ask_volume})

        deltas = []
        for t in trades[-200:]:
            side = t.get('S') or t.get('side', '')
            size = float(t.get('v') or t.get('size') or 0)
            deltas.append(size if str(side).lower() in {'buy', 'b'} else -size)
        trade_delta = float(np.sum(deltas)) if deltas else 0.0
        price_change = float(indicators['close'].iloc[-1] - indicators['close'].iloc[-10]) if len(indicators) > 10 else 0.0
        delta_div = trade_delta * np.sign(price_change) * -1

        absorption = min(1.0, abs(ofi) * 2)
        iceberg = min(1.0, np.std(deltas) / (np.mean(np.abs(deltas)) + 1e-9)) if deltas else 0.0

        sweeps.extend(stop_hunts)

        return LiquidityState(
            buy_side_pools=buy_side,
            sell_side_pools=sell_side,
            sweeps=sweeps,
            stop_hunts=stop_hunts,
            imbalances=imbalances,
            fvg_zones=fvg_zones,
            absorption_score=float(absorption),
            iceberg_score=float(iceberg),
            order_flow_imbalance=float(ofi),
            delta_divergence=float(delta_div),
        )
