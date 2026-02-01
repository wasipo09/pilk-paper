#!/usr/bin/env python3
"""
Telegram Trading Update Bot for Pilk Paper Trader
Pushes periodic updates to Telegram
"""
import sys
import json
import os
import subprocess
import time

# Telegram bot token from config
BOT_TOKEN = "8478921911:AAE4WrL1a9SRNuASKPWznGQ7HrYCv2ERU_o"
CHAT_ID = "5494376128"

PAPER_TRADER_DIR = "/home/ubuntu/.openclaw/workspace/pilk-paper"

def get_equity():
    """Get current equity from paper trader"""
    try:
        # Run the paper trader with status command
        result = subprocess.run(
            ['python3', 'paper_trader.py'],
            cwd=PAPER_TRADER_DIR,
            capture_output=True,
            text=True,
            timeout=15
        )

        # Parse the output to find equity
        output = result.stdout
        for line in output.split('\n'):
            if 'Total Equity:' in line:
                equity_line = line
                break
        else:
            # Fallback if parsing fails
            equity_line = output.split('Total Equity:')[1].strip() if 'Total Equity:' in output else "Equity: N/A"

        return equity_line
    except Exception as e:
        return f"Error fetching equity: {str(e)}"

def send_telegram_message(text):
    """Send a message to Telegram"""
    import requests

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    # Get current time
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Get equity
    equity_info = get_equity()

    # Build message
    message = f"""<b>📈 Pilk Paper Trader Update</b>

<b>Time:</b> {now}
{equity_info}

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
