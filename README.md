# Kotik Trading Analytics Terminal

Standalone Bybit (spot + linear futures) trading analytics and signal platform.

## What this provides
- **No Telegram bot component** (dashboard-centric architecture only).
- Real-time Bybit WebSocket ingest: candles, orderbook, trades, liquidations.
- REST metrics: open interest + funding rate.
- 20+ indicators: EMA/SMA, RSI, MACD, Stochastic, ADX, VWAP, ATR, Bollinger, Pivot, Fibonacci, Supertrend bands, Volume Profile bucket, Delta/CVD, HH/HL/LH/LL, Support/Resistance, candle patterns.
- Liquidity analytics: liquidity pools, sweeps, stop-hunts, fair value gaps, order-flow imbalance, delta divergence.
- Signal engine with >=90% probability gate + RR checks.
- Risk manager with position sizing and ATR/structure-based stop logic.
- FastAPI + WebSocket dashboard with symbol/timeframe controls and SL/TP recommendation form.

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## API
- `GET /api/health`
- `GET /api/state?symbol=BTCUSDT&timeframe=1`
- `POST /api/recommendation`
- `WS /api/ws/live?symbol=BTCUSDT&timeframe=1`
