from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class LiquidityMap:
    buy_side_pools: list[float]
    sell_side_pools: list[float]
    fvg_zones: list[dict[str, float | str]]
    stop_hunts: list[dict[str, float | str]]
    sweeps: list[dict[str, float | str]]
    order_flow_imbalance: float
    delta_divergence: float


class LiquidityEngine:
    @staticmethod
    def analyze(frame: pd.DataFrame, orderbook: dict[str, Any], trades: list[dict[str, Any]]) -> LiquidityMap:
        if frame.empty:
            return LiquidityMap([], [], [], [], [], 0.0, 0.0)

        highs = frame['high'].tail(100)
        lows = frame['low'].tail(100)
        buy_side = list(highs.nlargest(6).round(2))
        sell_side = list(lows.nsmallest(6).round(2))

        fvg, hunts = [], []
        recent = frame.tail(20).reset_index(drop=True)
        for i in range(2, len(recent)):
            p2 = recent.iloc[i - 2]
            cur = recent.iloc[i]
            p1 = recent.iloc[i - 1]
            if cur['low'] > p2['high']:
                fvg.append({'type': 'bullish', 'low': float(p2['high']), 'high': float(cur['low'])})
            if cur['high'] < p2['low']:
                fvg.append({'type': 'bearish', 'low': float(cur['high']), 'high': float(p2['low'])})
            if cur['high'] > p1['high'] and cur['close'] < p1['high']:
                hunts.append({'side': 'buy', 'level': float(p1['high'])})
            if cur['low'] < p1['low'] and cur['close'] > p1['low']:
                hunts.append({'side': 'sell', 'level': float(p1['low'])})

        bids = orderbook.get('b', []) if isinstance(orderbook, dict) else []
        asks = orderbook.get('a', []) if isinstance(orderbook, dict) else []
        bid_vol = float(np.sum([float(x[1]) for x in bids[:30]])) if bids else 0.0
        ask_vol = float(np.sum([float(x[1]) for x in asks[:30]])) if asks else 0.0
        ofi = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) else 0.0

        deltas = []
        for t in trades[-300:]:
            side = str(t.get('S') or t.get('side') or '').lower()
            size = float(t.get('v') or t.get('size') or 0)
            deltas.append(size if side in {'buy', 'b'} else -size)
        trade_delta = float(np.sum(deltas)) if deltas else 0.0
        px_delta = float(frame['close'].iloc[-1] - frame['close'].iloc[-8]) if len(frame) > 8 else 0.0
        div = trade_delta * np.sign(px_delta) * -1

        return LiquidityMap(
            buy_side_pools=buy_side,
            sell_side_pools=sell_side,
            fvg_zones=fvg,
            stop_hunts=hunts,
            sweeps=hunts,
            order_flow_imbalance=float(ofi),
            delta_divergence=float(div),
        )
