# Pilk Paper Trader Manual 📈

Welcome to the **Pilk Paper Trader**, a professional-grade cryptocurrency futures simulator running in your CLI. Test your strategies with **Isolated Margin**, **Leverage** (1x-50x), and real-time **Binance Futures** market data—risk-free.

---

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start a New Game** (Resets balance to $1,000):
   ```bash
   python paper_trader.py --new
   ```

3. **Continue Playing**:
   ```bash
   python paper_trader.py
   ```

---

## 🎮 Game Rules

### The Goal
You start with **$1,000 USDT**. Your goal is to grow this capital.
- **Game Over**: If your Total Equity drops below **$5.00**, you are bankrupt.
- **Winning**: There is no cap. How high can you go?

### Trading Mechanics (Important!)
This game simulates **Isolated Margin** futures trading.

1.  **Margin**: The specific amount of USDT you put up as collateral for a trade.
2.  **Leverage**: Multiplies your buying power (1x to 50x).
3.  **Liquidation**:
    - If your position's **Unrealized Loss** equals or exceeds your **Margin**, you are **LIQUIDATED**.
    - You lose 100% of the margin allocated to that trade.
    - Your remaining account balance is safe (Isolated Margin).

> **Example**:
> You open `long BTC/USDT 100 20`.
> - Margin: $100
> - Leverage: 20x
> - Position Size: $2,000
>
> If BTC price drops **5%**, your position loses 5% of $2,000 = $100.
> **Result**: You are liquidated. Your $100 is gone.

### Fees
Fees are realistic and deducted from your **Available Balance** (not margin) immediately.
- **Taker Fee**: 0.05% of the total position size (Notional Value).
- *Tip: High leverage = High position size = High fees!*

---

## 🕹 Command Reference

### `status`
View your live portfolio dashboard.
- **Symbol**: Asset name.
- **Side/Lev**: Long/Short and Leverage.
- **Margin**: Collateral locked.
- **Liq Price**: **CRITICAL**. If price hits this, you lose the position.
- **PnL**: Profit or Loss in USDT.
- **ROE%**: Return on Equity (Profit / Margin).

### `long <SYMBOL> <MARGIN> <LEVERAGE>`
Open a position profiting from price increases.
- **Usage**: `long BTC 100 10`
- *Meaning*: Bet on Bitcoin using $100 collateral at 10x leverage.

### `short <SYMBOL> <MARGIN> <LEVERAGE>`
Open a position profiting from price drops.
- **Usage**: `short ETH 50 5`
- *Meaning*: Bet against Ethereum using $50 collateral at 5x leverage.

### `close <SYMBOL>`
Close an open position at market price and realize PnL.
- **Usage**: `close BTC`
- *Note*: You can only close the entire position in this version.

### `history`
View a log of your last 15 actions (Opens, Closes, Liquidations).
- Full history is saved to `history.csv`.

### `quit` or `exit`
Save and Close the game.

---

## 🧩 Advanced Details

- **Global Refresh**: Every time you enter a command, the game fetches fresh prices for **ALL** your positions in real-time. If a price spike occurred while you were thinking, you might instantly see a liquidation message.
- **Symbol Resolution**: You can type `BTC/USDT`, `BTC`, or `BTC/USDT:USDT`. The game is smart enough to find the correct futures ticker on Binance.
- **Files**:
  - `trade_log.json`: Stores your active session state.
  - `history.csv`: A permanent record of every trade you've ever made.

---

## ⚠️ Troubleshooting

- **"Symbol not found"**: Ensure you are trading a valid USDT-M Future pair (e.g., `BTC/USDT`, `ETH/USDT`, `DOGE/USDT`).
- **Network Errors**: The game relies on the public Binance API. Rate limits or connection issues may cause occasional delays. Just try again.

Good luck! 🌕 magnitude
