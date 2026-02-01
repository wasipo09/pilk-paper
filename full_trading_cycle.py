#!/usr/bin/env python3
"""
Complete autonomous trading cycle
Runs position analysis + updates Telegram
"""
import subprocess
import sys

# Run autonomous analysis
print("=" * 60)
print("Pilk Autonomous Trading Analysis")
print("=" * 60)
proc = subprocess.run(
    ['venv/bin/python', 'autonomous_trader.py'],
    cwd='/home/ubuntu/.openclaw/workspace/pilk-paper',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    timeout=20
)

print(proc.stdout)
if proc.stderr:
    print("Errors:", proc.stderr)

# Update Telegram
print("\nUpdating Telegram...")
telegram_proc = subprocess.run(
    ['python3', 'telegram_update.py'],
    cwd='/home/ubuntu/.openclaw/workspace/pilk-paper',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    timeout=15
)

print(telegram_proc.stdout)
if telegram_proc.stderr:
    print("Telegram errors:", telegram_proc.stderr)

print("\nComplete. Check logs at: /tmp/pilk_trading_cycle.log")
