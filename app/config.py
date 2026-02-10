from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Kotik Trading Terminal'
    env: str = 'production'
    bybit_api_key: str = Field(default='')
    bybit_api_secret: str = Field(default='')
    bybit_rest_url: str = 'https://api.bybit.com'
    bybit_ws_public_url: str = 'wss://stream.bybit.com/v5/public/linear'
    bybit_ws_spot_url: str = 'wss://stream.bybit.com/v5/public/spot'

    symbols: list[str] = ['BTCUSDT']
    max_risk_per_trade: float = 0.01
    max_trades_per_hour: int = 5
    blocked_funding_rate: float = 0.001
    signal_probability_threshold: float = 0.90
    min_conditions_for_signal: int = 12


settings = Settings()
