from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp
import websockets

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    symbol: str
    timestamp: str
    klines: dict[str, list[dict[str, Any]]]
    orderbook: dict[str, Any]
    trades: list[dict[str, Any]]
    liquidations: list[dict[str, Any]]
    funding_rate: float | None
    open_interest: float | None


class BybitDataHub:
    def __init__(self) -> None:
        self.klines: dict[str, dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=2000)))
        self.orderbook: dict[str, dict[str, Any]] = defaultdict(dict)
        self.trades: dict[str, deque] = defaultdict(lambda: deque(maxlen=3000))
        self.liquidations: dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.funding_rate: dict[str, float] = {}
        self.open_interest: dict[str, float] = {}
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._ws_linear()),
            asyncio.create_task(self._ws_spot()),
            asyncio.create_task(self._poll_metrics()),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    async def _ws_linear(self) -> None:
        while True:
            try:
                async with websockets.connect(settings.bybit_ws_linear_url, ping_interval=20, ping_timeout=20) as ws:
                    args = []
                    for s in settings.symbols:
                        args += [f'orderbook.200.{s}', f'publicTrade.{s}', f'liquidation.{s}']
                        for tf in settings.timeframes:
                            args.append(f'kline.{tf}.{s}')
                    await ws.send(json.dumps({'op': 'subscribe', 'args': args}))
                    async for raw in ws:
                        self._route_message(json.loads(raw))
            except Exception as exc:
                logger.warning('linear reconnect: %s', exc)
                await asyncio.sleep(2)

    async def _ws_spot(self) -> None:
        while True:
            try:
                async with websockets.connect(settings.bybit_ws_spot_url, ping_interval=20, ping_timeout=20) as ws:
                    args = []
                    for s in settings.symbols:
                        args += [f'orderbook.200.{s}', f'publicTrade.{s}']
                    await ws.send(json.dumps({'op': 'subscribe', 'args': args}))
                    async for raw in ws:
                        self._route_message(json.loads(raw))
            except Exception as exc:
                logger.warning('spot reconnect: %s', exc)
                await asyncio.sleep(2)

    def _route_message(self, msg: dict[str, Any]) -> None:
        topic = msg.get('topic', '')
        payload = msg.get('data')
        if not topic or payload is None:
            return
        if topic.startswith('kline.'):
            _, tf, symbol = topic.split('.')
            row = payload[0] if isinstance(payload, list) else payload
            self.klines[symbol][tf].append(row)
        elif topic.startswith('orderbook.'):
            self.orderbook[topic.split('.')[-1]] = payload
        elif topic.startswith('publicTrade.'):
            symbol = topic.split('.')[-1]
            rows = payload if isinstance(payload, list) else [payload]
            for r in rows:
                self.trades[symbol].append(r)
        elif topic.startswith('liquidation.'):
            symbol = topic.split('.')[-1]
            rows = payload if isinstance(payload, list) else [payload]
            for r in rows:
                self.liquidations[symbol].append(r)

    async def _poll_metrics(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                for symbol in settings.symbols:
                    try:
                        oi = f'{settings.bybit_rest_url}/v5/market/open-interest?category=linear&symbol={symbol}&intervalTime=5min'
                        fr = f'{settings.bybit_rest_url}/v5/market/funding/history?category=linear&symbol={symbol}&limit=1'
                        async with session.get(oi) as r:
                            data = await r.json()
                            rows = data.get('result', {}).get('list', [])
                            if rows:
                                self.open_interest[symbol] = float(rows[0].get('openInterest', 0))
                        async with session.get(fr) as r:
                            data = await r.json()
                            rows = data.get('result', {}).get('list', [])
                            if rows:
                                self.funding_rate[symbol] = float(rows[0].get('fundingRate', 0))
                    except Exception as exc:
                        logger.warning('metric poll for %s failed: %s', symbol, exc)
                await asyncio.sleep(30)

    def snapshot(self, symbol: str) -> Snapshot:
        return Snapshot(
            symbol=symbol,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            klines={k: list(v) for k, v in self.klines[symbol].items()},
            orderbook=self.orderbook.get(symbol, {}),
            trades=list(self.trades[symbol]),
            liquidations=list(self.liquidations[symbol]),
            funding_rate=self.funding_rate.get(symbol),
            open_interest=self.open_interest.get(symbol),
        )
