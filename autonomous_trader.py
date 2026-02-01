#!/usr/bin/env python3
"""
Autonomous Pilk Paper Trader
Analyzes positions from trade_log.json only
"""
import json
import sys
import os
import time

PAPER_TRADER_DIR = "/home/ubuntu/.openclaw/workspace/pilk-paper"
TOLERANCE = 0.15  # Close if position is 15% underwater

def get_equity():
    """Get current equity from trade_log.json"""
    try:
        with open(os.path.join(PAPER_TRADER_DIR, 'trade_log.json'), 'r') as f:
            data = json.load(f)

            balance = data.get('balance', 1000)

            # Calculate equity from positions
            positions = data.get('positions', {})
            equity = balance

            for position_list in positions.values():
                for pos in position_list:
                    equity += pos['margin']

            return equity, balance
    except Exception as e:
        print(f"Error getting equity: {e}")
    return 0, 0

def get_current_price(symbol):
    """Get current price for a symbol using web fetch"""
    try:
        import requests
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return float(response.json()['price'])
    except:
        pass
    return None

def close_position(symbol):
    """Close a position"""
    try:
        print(f"Closing {symbol}...")
        proc = subprocess.run(
            ['venv/bin/python', 'paper_trader.py'],
            cwd=PAPER_TRADER_DIR,
            input=f'close {symbol}\n',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )

        output = proc.stdout
        if 'Closed' in output or 'Closing' in output:
            print(f"Closed {symbol}")
            return True

        return False
    except Exception as e:
        print(f"Error closing {symbol}: {e}")
        return False

def open_position(symbol, side, margin, leverage):
    """Open a new position"""
    try:
        print(f"Opening {side} {symbol} {leverage}x with ${margin} margin...")

        # Get current price first
        price = get_current_price(symbol)
        if not price:
            print(f"Cannot get price for {symbol}")
            return False

        # Open position
        proc = subprocess.run(
            ['venv/bin/python', 'paper_trader.py'],
            cwd=PAPER_TRADER_DIR,
            input=f'{side} {symbol} {margin} {leverage}\n',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )

        output = proc.stdout
        if side.upper() in output and 'Opened' in output:
            print(f"Opened {side} {symbol}")
            return True

        return False
    except Exception as e:
        print(f"Error opening position: {e}")
        return False

def analyze_positions():
    """Analyze positions and make trading decisions"""
    equity, balance = get_equity()

    try:
        with open(os.path.join(PAPER_TRADER_DIR, 'trade_log.json'), 'r') as f:
            data = json.load(f)
            positions = data.get('positions', {})
    except:
        positions = {}

    if not positions:
        print("No positions open")
        return

    print(f"\n{'='*60}")
    print(f"Portfolio Analysis - Equity: ${equity:.2f}")
    print(f"{'='*60}")

    total_margin = 0
    total_unrealized_pnl = 0
    has_major_drawdown = False

    for symbol, position_list in positions.items():
        for pos in position_list:
            margin = pos['margin']
            size = pos['size']
            entry_price = pos['entry_price']
            liq_price = pos['liq_price']
            position_type = pos['type']
            leverage = pos['leverage']

            # Get current price from Binance API
            price = get_current_price(symbol)
            if not price:
                price = entry_price  # Fallback

            # Calculate PnL
            if position_type == 'long':
                pnl = (price - entry_price) * size
            else:
                pnl = (entry_price - price) * size

            total_margin += margin
            total_unrealized_pnl += pnl

            roe = (pnl / margin) * 100 if margin > 0 else 0

            print(f"\n{symbol}:")
            print(f"  Type: {position_type.upper()} {leverage}x")
            print(f"  Margin: ${margin:.2f} | Entry: ${entry_price:.2f}")
            print(f"  Current: ${price:.2f} | PnL: ${pnl:.2f} ({roe:.1f}%)")
            print(f"  Liq Price: ${liq_price:.2f}")

            # Risk management decisions
            if position_type == 'long' and price <= liq_price:
                print(f"  LIQUIDATION IMMINENT! Price at {price:.2f} below liq at {liq_price:.2f}")
                close_position(symbol)
            elif position_type == 'short' and price >= liq_price:
                print(f"  LIQUIDATION IMMINENT! Price at {price:.2f} above liq at {liq_price:.2f}")
                close_position(symbol)
            elif pnl < 0 and (pnl / margin) < -TOLERANCE:
                print(f"  Position 15%+ underwater. Closing.")
                close_position(symbol)
            elif roe > 5:
                print(f"  Profitable (5%+). Keep holding.")
            elif roe < -5:
                print(f"  Deep drawdown (-5%+). Consider reducing.")

            if (pnl / margin) < -TOLERANCE:
                has_major_drawdown = True

    print(f"\n{'='*60}")
    print(f"Total: Margin ${total_margin:.2f} | PnL ${total_unrealized_pnl:.2f}")
    print(f"{'='*60}\n")

    # Check overall portfolio health
    if has_major_drawdown:
        print(f"WARNING: Major drawdown detected. Consider reducing exposure.")
    elif equity < 1000 and len(positions) > 0:
        print(f"Equity below $1,000 with open positions. Consider reducing risk.")

def main():
    print(f"\n{'='*60}")
    print(f"Pilk Autonomous Trader - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    analyze_positions()

    print(f"\nAnalysis complete. Check logs at: /tmp/pilk_trading_cycle.log")

if __name__ == '__main__':
    main()
