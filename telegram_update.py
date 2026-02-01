#!/usr/bin/env python3
"""
Telegram Trading Update Bot for Pilk Paper Trader
Pushes periodic updates to Telegram (plain text)
Directly reads trade_log.json instead of running interactive trader
"""
import sys
import json
import os
import time

# Telegram bot token from config
BOT_TOKEN = "8478921911:AAE4WrL1a9SRNuASKPWznGQ7HrYCv2ERU_o"
CHAT_ID = "5494376128"

PAPER_TRADER_DIR = "/home/ubuntu/.openclaw/workspace/pilk-paper"
TRADE_LOG_FILE = os.path.join(PAPER_TRADER_DIR, "trade_log.json")

def get_equity():
    """Get current equity from trade_log.json"""
    try:
        with open(TRADE_LOG_FILE, 'r') as f:
            data = json.load(f)

            balance = data.get('balance', 0)

            positions = data.get('positions', {})
            if not positions:
                equity = balance
            else:
                total_unrealized_pnl = 0
                for position_list in positions.values():
                    for pos in position_list:
                        margin = pos.get('margin', 0)

                        # Get current price from paper trader or use entry
                        try:
                            proc = subprocess.run(
                                ['venv/bin/python', 'paper_trader.py'],
                                cwd=PAPER_TRADER_DIR,
                                input='status\nquit\n',
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                            output = proc.stdout

                            # Find current price for this symbol
                            price = None
                            for line in output.split('\n'):
                                if pos.get('feed_symbol') in line and 'Price' in line:
                                    parts = line.split()
                                    for part in parts:
                                        clean = part.replace(',', '').replace('$', '').replace(':', '')
                                        if clean.replace('.', '', 1).isdigit():
                                            price = float(clean.replace('.', '', 1))
                                            break
                                    break
                        except:
                            price = pos.get('entry_price')

                        if not price:
                            price = pos.get('entry_price', 0)

                        # Calculate PnL
                        entry_price = pos.get('entry_price', 0)
                        size = pos.get('size', 0)
                        pos_type = pos.get('type')

                        if entry_price > 0 and size > 0 and price > 0:
                            if pos_type == 'long':
                                pnl = (price - entry_price) * size
                            else:
                                pnl = (entry_price - price) * size
                            total_unrealized_pnl += pnl

                equity = balance + total_unrealized_pnl

            # Format Unrealized PnL with conditional
            unrealized_pnl_display = f"{total_unrealized_pnl:.2f}" if positions else "0.00"
            return f"Balance: ${balance:.2f} | Equity: ${equity:.2f} | Unrealized PnL: ${unrealized_pnl_display}"
    except FileNotFoundError:
        return "Error: trade_log.json not found"
    except json.JSONDecodeError:
        return "Error: trade_log.json is invalid JSON"
    except Exception as e:
        return f"Error fetching equity: {str(e)}"

def get_positions_summary():
    """Get positions summary"""
    try:
        with open(TRADE_LOG_FILE, 'r') as f:
            data = json.load(f)
            positions = data.get('positions', {})

            if not positions:
                return "No positions open"

            summary = []
            for symbol, position_list in positions.items():
                for pos in position_list:
                    margin = pos.get('margin', 0)
                    leverage = pos.get('leverage', 0)
                    pos_type = pos.get('type', 'long')
                    entry_price = pos.get('entry_price', 0)

                    summary.append(f"{symbol}: {pos_type.upper()} {leverage}x - ${margin} margin")

            return "\n".join(summary)
    except Exception as e:
        return f"Error reading positions: {str(e)}"

def send_telegram_message(text):
    """Send a message to Telegram (plain text)"""
    import subprocess

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        response = subprocess.run(
            ['curl', '-s', '-X', 'POST', '-H', 'Content-Type: application/json', '-d', f'{json.dumps(data)}', url],
            capture_output=True,
            text=True,
            timeout=10
        )
        return json.loads(response.stdout)
    except Exception as e:
        return {"error": str(e)}

def main():
    # Get current time
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Get equity and positions
    equity_info = get_equity()
    positions_summary = get_positions_summary()

    # Build message (plain text)
    message = f"""Pilk Paper Trader Update

Time: {now}
{equity_info}

Positions:
{positions_summary}

---
Reply with a command (long/short/close/status) or just chat.
"""

    # Send message
    print(f"Sending update to Telegram...")
    result = send_telegram_message(message)

    if "error" in result:
        print(f"Error sending message: {result['error']}")
        return 1

    print(f"Message sent successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
