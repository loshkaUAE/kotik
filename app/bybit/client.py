from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import aiohttp

from app.config import settings


class BybitPrivateClient:
    def __init__(self) -> None:
        self.api_key = settings.bybit_api_key
        self.api_secret = settings.bybit_api_secret
        self.base = settings.bybit_rest_url

    def _sign(self, payload: str) -> str:
        return hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        ts = str(int(time.time() * 1000))
        recv_window = '5000'
        query = '&'.join([f'{k}={v}' for k, v in sorted(params.items())])
        sign = self._sign(f'{ts}{self.api_key}{recv_window}{query}')
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-TIMESTAMP': ts,
            'X-BAPI-RECV-WINDOW': recv_window,
            'X-BAPI-SIGN': sign,
            'X-BAPI-SIGN-TYPE': '2',
        }
        async with aiohttp.ClientSession() as session:
            async with session.request(method, f'{self.base}{path}', params=params, headers=headers) as resp:
                return await resp.json()
