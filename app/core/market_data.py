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
class MarketSnapshot:
    symbol: str
    timestamp: datetime
    klines: dict[str, list[dict[str, Any]]]
    orderbook: dict[str, Any]
    open_interest: float | None
    funding_rate: float | None
    liquidations: list[dict[str, Any]]
    trades: list[dict[str, Any]]


class BybitMarketDataClient:
    def __init__(self, symbols: list[str] | None = None) -> None:
        self.symbols = symbols or settings.symbols
        self.klines: dict[str, dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        self.orderbook: dict[str, dict[str, Any]] = defaultdict(dict)
        self.open_interest: dict[str, float] = {}
        self.funding_rate: dict[str, float] = {}
        self.liquidations: dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.trades: dict[str, deque] = defaultdict(lambda: deque(maxlen=2000))
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self._tasks.extend([
            asyncio.create_task(self._stream_linear()),
            asyncio.create_task(self._stream_spot()),
            asyncio.create_task(self._poll_rest_metrics()),
        ])

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    async def _stream_linear(self) -> None:
        while True:
            try:
                async with websockets.connect(settings.bybit_ws_public_url, ping_interval=20, ping_timeout=20) as ws:
                    args = []
                    for symbol in self.symbols:
                        args.extend([
                            f'kline.1.{symbol}', f'kline.5.{symbol}', f'kline.15.{symbol}', f'kline.60.{symbol}',
                            f'orderbook.200.{symbol}', f'publicTrade.{symbol}', f'liquidation.{symbol}',
                        ])
                    await ws.send(json.dumps({'op': 'subscribe', 'args': args}))
                    async for raw in ws:
                        self._handle_ws_message(json.loads(raw))
            except Exception as exc:
                logger.warning('linear websocket reconnecting: %s', exc)
                await asyncio.sleep(2)

    async def _stream_spot(self) -> None:
        while True:
            try:
                async with websockets.connect(settings.bybit_ws_spot_url, ping_interval=20, ping_timeout=20) as ws:
                    args = []
                    for symbol in self.symbols:
                        args.extend([f'orderbook.200.{symbol}', f'publicTrade.{symbol}'])
                    await ws.send(json.dumps({'op': 'subscribe', 'args': args}))
                    async for raw in ws:
                        self._handle_ws_message(json.loads(raw))
            except Exception as exc:
                logger.warning('spot websocket reconnecting: %s', exc)
                await asyncio.sleep(2)

    def _handle_ws_message(self, message: dict[str, Any]) -> None:
        topic = message.get('topic', '')
        data = message.get('data')
        if not topic or data is None:
            return

        if topic.startswith('kline.'):
            _, interval, symbol = topic.split('.')
            payload = data[0] if isinstance(data, list) else data
            self.klines[symbol][interval].append(payload)
        elif topic.startswith('orderbook.'):
            symbol = topic.split('.')[-1]
            self.orderbook[symbol] = data
        elif topic.startswith('liquidation.'):
            symbol = topic.split('.')[-1]
            records = data if isinstance(data, list) else [data]
            for rec in records:
                self.liquidations[symbol].append(rec)
        elif topic.startswith('publicTrade.'):
            symbol = topic.split('.')[-1]
            records = data if isinstance(data, list) else [data]
            for rec in records:
                self.trades[symbol].append(rec)

    async def _poll_rest_metrics(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                try:
                    for symbol in self.symbols:
                        oi_url = f"{settings.bybit_rest_url}/v5/market/open-interest?category=linear&symbol={symbol}&intervalTime=5min"
                        fr_url = f"{settings.bybit_rest_url}/v5/market/funding/history?category=linear&symbol={symbol}&limit=1"
                        async with session.get(oi_url) as resp:
                            oi_json = await resp.json()
                            rows = oi_json.get('result', {}).get('list', [])
                            if rows:
                                self.open_interest[symbol] = float(rows[0].get('openInterest', 0.0))
                        async with session.get(fr_url) as resp:
                            fr_json = await resp.json()
                            rows = fr_json.get('result', {}).get('list', [])
                            if rows:
                                self.funding_rate[symbol] = float(rows[0].get('fundingRate', 0.0))
                except Exception as exc:
                    logger.warning('rest poll failed: %s', exc)
                await asyncio.sleep(30)

    def snapshot(self, symbol: str) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol,
            timestamp=datetime.now(tz=timezone.utc),
            klines={k: list(v) for k, v in self.klines[symbol].items()},
            orderbook=self.orderbook.get(symbol, {}),
            open_interest=self.open_interest.get(symbol),
            funding_rate=self.funding_rate.get(symbol),
            liquidations=list(self.liquidations[symbol]),
            trades=list(self.trades[symbol]),
        )
