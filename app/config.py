from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Kotik Trading Analytics Terminal'
    bybit_api_key: str = ''
    bybit_api_secret: str = ''
    bybit_rest_url: str = 'https://api.bybit.com'
    bybit_ws_linear_url: str = 'wss://stream.bybit.com/v5/public/linear'
    bybit_ws_spot_url: str = 'wss://stream.bybit.com/v5/public/spot'

    symbols: list[str] = ['BTCUSDT', 'ETHUSDT']
    timeframes: list[str] = ['1', '5', '15', '60']

    signal_probability_threshold: float = 0.90
    min_conditions_for_signal: int = 12
    max_risk_per_trade: float = 0.01
    default_balance: float = 10_000


settings = Settings()
