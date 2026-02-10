# Kotik Trading Terminal

Production-oriented crypto analytics and signal platform for Bybit spot + linear futures.

## Features
- FastAPI backend + websocket broadcast.
- Multi-source market data (kline, orderbook, trades, liquidations, open interest, funding).
- 20+ indicators and market structure signals.
- Liquidity + smart money analytics (pools, stop hunts, FVG, imbalance, absorption, iceberg score).
- Signal engine with 12+ condition alignment and probability threshold.
- Risk management (position sizing, leverage, liquidation estimate, overtrading/revenge/funding blocks).
- Interactive dashboard with candlesticks, indicators, live setup panel.

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.
