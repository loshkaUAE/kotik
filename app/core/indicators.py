from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class IndicatorPack:
    frame: pd.DataFrame


class IndicatorsEngine:
    @staticmethod
    def from_klines(klines: list[dict]) -> IndicatorPack:
        if not klines:
            return IndicatorPack(frame=pd.DataFrame())
        df = pd.DataFrame(klines).copy()
        rename = {'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume', 'turnover': 'turnover'}
        df = df.rename(columns=rename)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['open', 'high', 'low', 'close']).reset_index(drop=True)
        out = df.copy()

        out['ema_9'] = out['close'].ewm(span=9, adjust=False).mean()
        out['ema_21'] = out['close'].ewm(span=21, adjust=False).mean()
        out['ema_50'] = out['close'].ewm(span=50, adjust=False).mean()
        out['ema_200'] = out['close'].ewm(span=200, adjust=False).mean()

        delta = out['close'].diff()
        up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        down = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rs = up / down.replace(0, np.nan)
        out['rsi'] = 100 - (100 / (1 + rs))

        ema12 = out['close'].ewm(span=12, adjust=False).mean()
        ema26 = out['close'].ewm(span=26, adjust=False).mean()
        out['macd'] = ema12 - ema26
        out['macd_signal'] = out['macd'].ewm(span=9, adjust=False).mean()
        out['macd_hist'] = out['macd'] - out['macd_signal']

        typical = (out['high'] + out['low'] + out['close']) / 3
        out['vwap'] = (typical * out['volume']).cumsum() / out['volume'].replace(0, np.nan).cumsum()

        tr1 = out['high'] - out['low']
        tr2 = (out['high'] - out['close'].shift()).abs()
        tr3 = (out['low'] - out['close'].shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        out['atr'] = tr.rolling(14).mean()

        out['bb_mid'] = out['close'].rolling(20).mean()
        bb_std = out['close'].rolling(20).std()
        out['bb_up'] = out['bb_mid'] + 2 * bb_std
        out['bb_low'] = out['bb_mid'] - 2 * bb_std

        min14 = out['low'].rolling(14).min()
        max14 = out['high'].rolling(14).max()
        stoch = (out['close'] - min14) / (max14 - min14).replace(0, np.nan)
        out['stoch_rsi_k'] = stoch.rolling(3).mean() * 100
        out['stoch_rsi_d'] = out['stoch_rsi_k'].rolling(3).mean()

        plus_dm = out['high'].diff()
        minus_dm = -out['low'].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        tr_sum = tr.rolling(14).sum()
        plus_di = 100 * (plus_dm.rolling(14).sum() / tr_sum.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(14).sum() / tr_sum.replace(0, np.nan))
        dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        out['adx'] = dx.rolling(14).mean()

        out['tenkan'] = (out['high'].rolling(9).max() + out['low'].rolling(9).min()) / 2
        out['kijun'] = (out['high'].rolling(26).max() + out['low'].rolling(26).min()) / 2
        out['senkou_a'] = ((out['tenkan'] + out['kijun']) / 2).shift(26)
        out['senkou_b'] = ((out['high'].rolling(52).max() + out['low'].rolling(52).min()) / 2).shift(26)

        out['pivot'] = (out['high'].shift(1) + out['low'].shift(1) + out['close'].shift(1)) / 3
        out['r1'] = 2 * out['pivot'] - out['low'].shift(1)
        out['s1'] = 2 * out['pivot'] - out['high'].shift(1)

        swing_high = out['high'].rolling(50).max()
        swing_low = out['low'].rolling(50).min()
        diff = swing_high - swing_low
        out['fib_0_382'] = swing_high - diff * 0.382
        out['fib_0_618'] = swing_high - diff * 0.618

        hl2 = (out['high'] + out['low']) / 2
        factor = 3
        out['supertrend_up'] = hl2 - factor * out['atr']
        out['supertrend_down'] = hl2 + factor * out['atr']

        out['cum_volume'] = out['volume'].cumsum()
        out['volume_profile_node'] = pd.qcut(out['close'].rank(method='first'), q=10, labels=False, duplicates='drop')

        out['cvd'] = np.where(out['close'] >= out['open'], out['volume'], -out['volume']).cumsum()

        out['hh'] = out['high'] > out['high'].shift(1)
        out['hl'] = out['low'] > out['low'].shift(1)
        out['lh'] = out['high'] < out['high'].shift(1)
        out['ll'] = out['low'] < out['low'].shift(1)

        out['support'] = out['low'].rolling(20).min()
        out['resistance'] = out['high'].rolling(20).max()

        return IndicatorPack(frame=out)
