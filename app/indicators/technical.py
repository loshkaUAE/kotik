from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class IndicatorPack:
    frame: pd.DataFrame


class TechnicalIndicators:
    @staticmethod
    def calculate(klines: list[dict]) -> IndicatorPack:
        if not klines:
            return IndicatorPack(pd.DataFrame())
        df = pd.DataFrame(klines).copy()
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['open', 'high', 'low', 'close']).reset_index(drop=True)
        o = df

        # Trend and moving averages
        o['ema_9'] = o['close'].ewm(span=9, adjust=False).mean()
        o['ema_21'] = o['close'].ewm(span=21, adjust=False).mean()
        o['ema_50'] = o['close'].ewm(span=50, adjust=False).mean()
        o['ema_200'] = o['close'].ewm(span=200, adjust=False).mean()
        o['sma_20'] = o['close'].rolling(20).mean()
        o['sma_50'] = o['close'].rolling(50).mean()

        # RSI, MACD, Stochastic, ADX
        delta = o['close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        o['rsi'] = 100 - (100/(1+rs))

        ema12 = o['close'].ewm(span=12, adjust=False).mean()
        ema26 = o['close'].ewm(span=26, adjust=False).mean()
        o['macd'] = ema12 - ema26
        o['macd_signal'] = o['macd'].ewm(span=9, adjust=False).mean()
        o['macd_hist'] = o['macd'] - o['macd_signal']

        low14 = o['low'].rolling(14).min()
        high14 = o['high'].rolling(14).max()
        o['stoch_k'] = 100 * (o['close'] - low14) / (high14 - low14).replace(0, np.nan)
        o['stoch_d'] = o['stoch_k'].rolling(3).mean()

        tr = pd.concat([
            o['high'] - o['low'],
            (o['high'] - o['close'].shift()).abs(),
            (o['low'] - o['close'].shift()).abs(),
        ], axis=1).max(axis=1)
        o['atr'] = tr.rolling(14).mean()

        plus_dm = o['high'].diff().clip(lower=0)
        minus_dm = (-o['low'].diff()).clip(lower=0)
        tr14 = tr.rolling(14).sum()
        plus_di = 100 * plus_dm.rolling(14).sum() / tr14.replace(0, np.nan)
        minus_di = 100 * minus_dm.rolling(14).sum() / tr14.replace(0, np.nan)
        dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        o['adx'] = dx.rolling(14).mean()

        # VWAP, Bollinger, Pivots, Fib, Supertrend-like bands
        tp = (o['high'] + o['low'] + o['close']) / 3
        o['vwap'] = (tp * o['volume']).cumsum() / o['volume'].replace(0, np.nan).cumsum()
        o['bb_mid'] = o['close'].rolling(20).mean()
        std = o['close'].rolling(20).std()
        o['bb_up'] = o['bb_mid'] + 2 * std
        o['bb_low'] = o['bb_mid'] - 2 * std

        o['pivot'] = (o['high'].shift(1) + o['low'].shift(1) + o['close'].shift(1)) / 3
        o['r1'] = 2 * o['pivot'] - o['low'].shift(1)
        o['s1'] = 2 * o['pivot'] - o['high'].shift(1)

        sh = o['high'].rolling(55).max()
        sl = o['low'].rolling(55).min()
        rng = sh - sl
        o['fib_0_382'] = sh - 0.382 * rng
        o['fib_0_618'] = sh - 0.618 * rng

        hl2 = (o['high'] + o['low']) / 2
        o['supertrend_up'] = hl2 - 3 * o['atr']
        o['supertrend_dn'] = hl2 + 3 * o['atr']

        # Volume profile, delta, structure, support/resistance
        o['volume_profile_bucket'] = pd.qcut(o['close'].rank(method='first'), q=10, labels=False, duplicates='drop')
        o['delta'] = np.where(o['close'] >= o['open'], o['volume'], -o['volume'])
        o['cvd'] = o['delta'].cumsum()
        o['hh'] = o['high'] > o['high'].shift(1)
        o['hl'] = o['low'] > o['low'].shift(1)
        o['lh'] = o['high'] < o['high'].shift(1)
        o['ll'] = o['low'] < o['low'].shift(1)
        o['support'] = o['low'].rolling(20).min()
        o['resistance'] = o['high'].rolling(20).max()

        # Candle patterns
        body = (o['close'] - o['open']).abs()
        rng_c = (o['high'] - o['low']).replace(0, np.nan)
        upper_wick = o['high'] - o[['open', 'close']].max(axis=1)
        lower_wick = o[['open', 'close']].min(axis=1) - o['low']
        o['doji'] = (body / rng_c) < 0.1
        o['hammer'] = (lower_wick > 2 * body) & (upper_wick < body)
        prev_open = o['open'].shift(1)
        prev_close = o['close'].shift(1)
        o['bullish_engulfing'] = (prev_close < prev_open) & (o['close'] > o['open']) & (o['close'] >= prev_open) & (o['open'] <= prev_close)
        o['bearish_engulfing'] = (prev_close > prev_open) & (o['close'] < o['open']) & (o['open'] >= prev_close) & (o['close'] <= prev_open)

        return IndicatorPack(o)
