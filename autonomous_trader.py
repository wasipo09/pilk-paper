#!/usr/bin/env python3
"""
Autonomous Pilk Paper Trader
Analyzes positions, manages risk, trades based on signals
"""
import subprocess
import json
import sys
import os
import time

PAPER_TRADER_DIR = "/home/ubuntu/.openclaw/workspace/pilk-paper"
TOLERANCE = 0.15  # Close if position is 15% underwater
MAX_DRAWDOWN_PER_POSITION = 0.10  # Max 10% of margin can be lost per position
MAX_TOTAL_DRAWDOWN = 0.20  # Max 20% total portfolio drawdown

def get_equity():
    """Get current equity"""
    try:
        proc = subprocess.run(
            ['venv/bin/python', 'paper_trader.py'],
            cwd=PAPER_TRADER_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )

        output = proc.stdout
        for line in output.split('\n'):
            if 'Total Equity:' in line:
                return float(line.split('Total Equity:')[1].strip().replace('USDT', '').replace(',', '').strip())
    except Exception as e:
        print(f"Error getting equity: {e}")
    return 0

def get_positions():
    """Get current positions"""
    try:
        with open(os.path.join(PAPER_TRADER_DIR, 'trade_log.json'), 'r') as f:
            data = json.load(f)
            return data.get('positions', {})
    except Exception as e:
        print(f"Error reading positions: {e}")
    return {}

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
            timeout=15
        )

        output = proc.stdout
        if 'Closed' in output or 'Closing' in output:
            print(f"✓ Closed {symbol}")
            return True

        # If output is empty, check stderr
        if proc.stderr:
            print(f"Output: {output}")
            print(f"Stderr: {proc.stderr}")

        return False
    except Exception as e:
        print(f"Error closing {symbol}: {e}")
        return False

def open_position(symbol, side, margin, leverage):
    """Open a new position"""
    try:
        print(f"Opening {side} {symbol} {leverage}x with ${margin} margin...")

        # Get current price
        proc = subprocess.run(
            ['venv/bin/python', 'paper_trader.py'],
            cwd=PAPER_TRADER_DIR,
            input=f'{side} {symbol} {margin} {leverage}\n',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )

        output = proc.stdout
        if side.upper() in output and 'Opened' in output:
            print(f"✓ Opened {side} {symbol}")
            return True

        if proc.stderr:
            print(f"Output: {output}")
            print(f"Stderr: {proc.stderr}")

        return False
    except Exception as e:
        print(f"Error opening position: {e}")
        return False

def analyze_positions():
    """Analyze positions and make trading decisions"""
    equity = get_equity()
    balance = 0
    positions = get_positions()

    if not positions:
        print("No positions open")
        return

    print(f"\n{'='*60}")
    print(f"Portfolio Analysis - Equity: ${equity:.2f}")
    print(f"{'='*60}")

    total_margin = 0
    total_unrealized_pnl = 0

    for symbol, position_list in positions.items():
        for pos in position_list:
            margin = pos['margin']
            size = pos['size']
            entry_price = pos['entry_price']
            liq_price = pos['liq_price']
            position_type = pos['type']
            leverage = pos['leverage']

            # Get current price
            try:
                proc = subprocess.run(
                    ['venv/bin/python', 'paper_trader.py'],
                    cwd=PAPER_TRADER_DIR,
                    input='status\nquit\n',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )

                output = proc.stdout
                # Find current price for this symbol
                price = None
                for line in output.split('\n'):
                    if symbol in line and 'Price' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.replace(',', '').replace('$', '').isdigit():
                                price = float(part.replace(',', '').replace('$', ''))
                                break
                        break

                if not price:
                    price = entry_price  # Fallback

                # Calculate PnL
                if position_type == 'long':
                    pnl = (price - entry_price) * size
                else:
                    pnl = (entry_price - price) * size

                total_margin += margin
                total_unrealized_pnl += pnl

                roe = (pnl / margin) * 100

                print(f"\n{symbol}:")
                print(f"  Type: {position_type.upper()} {leverage}x")
                print(f"  Margin: ${margin:.2f} | Entry: ${entry_price:.2f}")
                print(f"  Current: ${price:.2f} | PnL: ${pnl:.2f} ({roe:.1f}%)")
                print(f"  Liq Price: ${liq_price:.2f}")

                # Risk management decisions
                if position_type == 'long' and price <= liq_price:
                    print(f"  ⚠️  LIQUIDATION IMMINENT! Price at {price:.2f} below liq at {liq_price:.2f}")
                    close_position(symbol)
                elif position_type == 'short' and price >= liq_price:
                    print(f"  ⚠️  LIQUIDATION IMMINENT! Price at {price:.2f} above liq at {liq_price:.2f}")
                    close_position(symbol)
                elif pnl < 0 and (pnl / margin) < -TOLERANCE:
                    print(f"  ⚠️  Position 15%+ underwater. Consider closing.")
                    # Close it (aggressive)
                    close_position(symbol)
                elif roe > 5:
                    print(f"  ✓ Profitable (5%+). Keep holding.")

            except Exception as e:
                print(f"  Error analyzing position: {e}")

    print(f"\n{'='*60}")
    print(f"Total: Margin ${total_margin:.2f} | PnL ${total_unrealized_pnl:.2f}")
    print(f"{'='*60}\n")

    # Check overall portfolio health
    if total_unrealized_pnl < -MAX_DRAWDOWN_PER_POSITION * total_margin:
        print(f"⚠️  Major drawdown. Consider reducing exposure.")
        # Close highest loss position
        # (Simplified: just warn for now)
    elif equity < 1000 and len(positions) > 0:
        print(f"⚠️  Equity below $1,000 with open positions. Consider reducing risk.")

def main():
    print(f"\n{'='*60}")
    print(f"Pilk Autonomous Trader - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    analyze_positions()

    print(f"Analysis complete. Check logs at: /tmp/pilk_telegram_updates.log")

if __name__ == '__main__':
    main()
