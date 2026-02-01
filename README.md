# Pilk Paper Trader

A realistic command-line interface (CLI) game for paper trading cryptocurrency futures on Binance (USDT-M).

Test your trading strategies, practice risk management, and experience the thrill of leverage without risking real money.

## Features

- **Real-Time Data**: Fetches live market prices from Binance Futures via `ccxt`.
- **Realistic Simulation**:
    - **Isolated Margin**: Manage risk per position.
    - **Leverage (1x-50x)**: Amplify gains (and losses).
    - **Fees**: Simulate real exchange fees (0.05% Taker).
    - **Liquidation**: Positions are automatically wiped out if margin is depleted.
- **Advanced Order Types**:
    - **Limit Orders**: Place orders that trigger at specific prices.
    - **Take Profit (TP) & Stop Loss (SL)**: Automate your exits.
- **Persistent State**: Your balance, positions, and orders are saved automatically.
- **Performance Tracking**: Detailed transaction history (`history.csv`) and PnL analysis.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/rentamac/pilk-paper.git
    cd pilk-paper
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## How to Play

Start the game by running:

```bash
python paper_trader.py
```

- You start with **1000 USDT**.
- If your equity drops below **5 USDT**, it's GAME OVER.
- Use `--new` to restart with a fresh balance:
    ```bash
    python paper_trader.py --new
    ```

### Command Reference

| Command | Alias | Description | Usage |
| :--- | :--- | :--- | :--- |
| `long` | `b`, `buy` | Open a Long position | `b <symbol> <margin> <leverage> [--tp price] [--sl price]` |
| `short` | `s`, `sell` | Open a Short position | `s <symbol> <margin> <leverage> [--tp price] [--sl price]` |
| `close` | `c` | Close a position | `c <symbol>` |
| `limit` | - | Place a Limit Order | `limit <long/short> <symbol> <price> <margin> <leverage>` |
| `status` | `st` | View portfolio & prices | `st` |
| `history` | `h` | View last 15 trades | `h` |
| `quit` | `exit` | Save and exit | `quit` |

### Examples

**1. Open a Long Position (Buy)**
Bet 100 USDT on BTC with 10x leverage.
```bash
> b BTC 100 10
```

**2. Open with Take Profit & Stop Loss**
Long ETH with 50 USDT at 20x. Take profit at 4000, Stop loss at 3000.
```bash
> b ETH 50 20 --tp 4000 --sl 3000
```

**3. Place a Limit Order**
Set a Limit Buy (Long) for SOL if price drops to 80.
```bash
> limit long SOL 80 50 5
```
*The position will automatically open when the price crosses your limit.*

**4. Close a Position**
Market close your BTC position.
```bash
> c BTC
```

**5. Check Status**
See your current PnL, open positions, and orders.
```bash
> st
```

## Game Mechanics

### Margin & Leverage
- **Margin**: The amount of your own cash you lock into a trade.
- **Leverage**: Multiplies your buying power. 100 USDT margin at 10x leverage = 1000 USDT position size.
- **Risk**: Higher leverage means the price needs to move less against you to cause liquidation.

### Fees
- **Taker Fee**: 0.05% of the *total position size* (Not just margin).
- Example: 100 Margin x 10 Leverage = 1000 Size. Fee = 1000 * 0.0005 = 0.50 USDT.

### Liquidation
- If your PnL drops roughly equal to your Margin, the position is **Liquidated**.
- You lose the entire margin amount for that trade.
- **Simulated Mechanic**: We check `Margin + PnL <= 0`. If true, the position is removed and margin is lost.

### Take Profit / Stop Loss
- Checks are performed every time the portfolio updates (every command loop).
- If the current market price crosses your trigger, the mechanism executes a market close immediately.

## Data & Strategy
- Prices are live from Binance Futures.
- Use `history.csv` to analyze your trading performance in Excel/Sheets.
