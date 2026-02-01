# Autonomous Pilk Paper Trading System

## Overview

Your Ethereum futures trading is now fully autonomous. The system runs on its own, managing risk, analyzing positions, and trading based on signals.

## Current Configuration

### Trading Cycle
- **Check frequency**: Every 10 minutes
- **Telegram updates**: Every 30 minutes
- **Log files**:
  - Trading analysis: `/tmp/pilk_trading_cycle.log`
  - Telegram updates: `/tmp/pilk_telegram_updates.log`

### Risk Parameters
- **Position close tolerance**: 15% underwater
- **Max drawdown per position**: 10% of margin
- **Max total portfolio drawdown**: 20%
- **Leverage limits**: 1x-50x

### Position Management
- Can hold multiple positions per symbol
- Automatically closes on liquidation or major drawdown
- Aggressive: Closes at 15%+ loss

## Current Portfolio Status

```
ETH/USDT LONG 5x     $50 margin     -4% PnL     Entry: $2429
ETH/USDT LONG 3x     $30 margin     -5% PnL     Entry: $2450
----------------------------------------------
Total Equity: $996.66
```

## News-Driven Strategy

The system monitors ETH news and market conditions:
- **Current**: ETH down 7% in January 2026
- **Outlook**: Price predictions point to $3,400 by Feb 2026
- **Signal**: Bullish - accumulating on dips

## Files

- `autonomous_trader.py` - Main analysis and trading logic
- `full_trading_cycle.py` - Complete cycle (analysis + Telegram update)
- `telegram_update.py` - Telegram notification bot
- `controller.py` - Interactive trader control

## Manual Controls

```bash
# Check positions and analyze
python3 full_trading_cycle.py

# Manual Telegram update
python3 telegram_update.py

# Run trader interactively
python3 paper_trader.py
```

## To Customize

### Change check interval
Edit crontab:
```bash
crontab -e
# Change */10 to */15, */30, */60, etc.
```

### Adjust risk tolerance
Edit `autonomous_trader.py`:
```python
TOLERANCE = 0.15  # 15% close threshold
MAX_DRAWDOWN_PER_POSITION = 0.10
MAX_TOTAL_DRAWDOWN = 0.20
```

### Change news source
Edit `autonomous_trader.py` - add more web_search calls or API integrations.

## Logs

Check latest trading decisions:
```bash
tail -f /tmp/pilk_trading_cycle.log
```

## Troubleshooting

If positions aren't being closed:
1. Check logs: `cat /tmp/pilk_trading_cycle.log`
2. Verify equity is being calculated correctly
3. Adjust tolerance in `autonomous_trader.py`

If Telegram updates aren't working:
```bash
python3 telegram_update.py
cat /tmp/pilk_telegram_updates.log
```

## Security

- Positions are managed via CLI only (no API keys exposed)
- All actions logged for review
- Risk management prevents overexposure
