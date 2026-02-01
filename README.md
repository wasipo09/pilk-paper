# pilk-paper

A simple, realistic crypto paper trading game running in your terminal. 
It uses real-time market data from Binance Futures (USDT-M) via `ccxt` to simulate trading.

## Features
- **Real-time Data**: Fetches live prices for USDT-M futures pairs (e.g., BTC/USDT).
- **Realistic Fees**:
  - Maker: 0.02% (Not implemented explicitly in Market orders, but variable exists)
  - Taker: 0.05% (Applied on all immediate entries/exits)
- **Portfolio Tracking**: Tracks positions, unrealized PnL, and account balance locally in `trade_log.json`.
- **Rich UI**: Uses `rich` for beautiful terminal tables and status updates.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Start the game:

```bash
python paper_trader.py
```

### Commands
- `status`: Show current portfolio, balance, and unrealized PnL.
- `long <SYMBOL> <USDT_AMOUNT>`: Open a Long position (e.g., `long BTC/USDT 1000`).
- `short <SYMBOL> <USDT_AMOUNT>`: Open a Short position.
- `close <SYMBOL>`: Close the entire position for a symbol at current market price.
- `history`: View trade history.
- `quit`: Exit the game.

## Data Source
Uses public Binance Futures API. No API keys required.
