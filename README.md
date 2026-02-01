# The Pilk Paper Trading Manual

Welcome to **Pilk Paper Trader**, a realistic cryptocurrency futures trading simulation running directly in your terminal. This tool allows you to practice trading with isolated margin, leverage, and real-time market data from Binance Futures, without risking real money.

## Table of Contents
1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Game Mechanics](#game-mechanics)
4. [Commands](#commands)
5. [Data & Privacy](#data--privacy)

## Installation

Ensure you have Python 3.8+ installed.

1. Clone this repository (or download the files).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Getting Started

To launch the game, run:
```bash
python paper_trader.py
```

### Starting a New Game
If you are playing for the first time or want to reset your progress:
```bash
python paper_trader.py --new
```
This resets your balance to **1,000 USDT**.

## Game Mechanics

### 1. The Goal
Grow your portfolio from **$1,000 USDT**. 
The game ends if your Total Equity (Balance + Unrealized PnL) drops below **$5.00**.

### 2. Isolated Margin & Leverage
Every trade is **Isolated**. This means you must specify exactly how much margin (collateral) you want to risk for that specific trade. 
- You also select **Leverage** (1x to 50x).
- **Notional Value** = Margin × Leverage.
- **Liquidation**: If your position's loss equals or exceeds your Margin, the position is **Liquidated**. You lose the entire margin amount for that trade, but the rest of your account balance is safe.

*Example:*
> You open a Long on BTC with $100 Margin at 10x Leverage.
> - Position Size: $1,000 worth of BTC.
> - If BTC drops by 10%, your position loses $100 (10% of $1,000).
> - Since Loss ($100) == Margin ($100), you are **Liquidated**.

### 3. Fees
Realism is key. Fees are deducted from your **Available Balance** immediately upon opening and closing trades.
- **Taker Fee**: 0.05% of Notional Value.
- **Maker Fee**: 0.02% (Not currently used as all orders are Market orders).

*Note: High leverage means higher fees relative to your margin!*

### 4. Real-time Updates
Every time you enter a command, the system fetches live prices for ALL your open positions. 
- **Liquidations are checked automatically.**
- If a position is liquidated, it is removed, and the loss is realized immediately.

## Commands

### Status
`status`
Displays your current portfolio, including:
- Margin usage per position
- Entry Price vs Mark Price
- **Liquidation Price** (Watch this closely!)
- Unrealized PnL and ROE %
- Total Account Equity

### Long (Buy)
`long <SYMBOL> <MARGIN> <LEVERAGE>`
Opens a long position. You profit if the price goes UP.
- Example: `long BTC/USDT 500 20`
- Meaning: Use 500 USDT collateral at 20x leverage (Total Position: $10,000).

### Short (Sell)
`short <SYMBOL> <MARGIN> <LEVERAGE>`
Opens a short position. You profit if the price goes DOWN.
- Example: `short ETH/USDT 100 5`

### Close
`close <SYMBOL>`
Closes the entire position for a symbol at market price.
- Example: `close BTC/USDT`

### History
`history`
Shows the last 15 recorded transactions (Opens, Closes, Liquidations).

### Quit
`quit` or `exit`
Saves your state and exits the game.

## Data & Privacy
- **Market Data**: Fetched continuously from Binance public API. No API keys are required.
- **Game Data**: Your trade history and balance are saved locally in `trade_log.json` and `history.csv`.
