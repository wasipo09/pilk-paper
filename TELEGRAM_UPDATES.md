# Telegram Updates for Pilk Paper Trader

Automated Telegram notifications for your paper trading positions.

## How it Works

A cron job runs `telegram_update.py` every 30 minutes, fetching your current equity and sending a summary to your Telegram.

## Current Configuration

- **Interval**: Every 30 minutes
- **Script**: `/home/ubuntu/.openclaw/workspace/pilk-paper/telegram_update.py`
- **Chat ID**: `5494376128`
- **Log File**: `/tmp/pilk_telegram_updates.log`

## Manual Updates

Run manually:
```bash
cd /home/ubuntu/.openclaw/workspace/pilk-paper
python3 telegram_update.py
```

## Customize Time Interval

Edit the cron schedule:
```bash
crontab -e
```

Examples:
- Every 15 minutes: `*/15 * * * *`
- Every hour: `0 * * * *`
- Every 2 hours: `0 */2 * * *`

## Troubleshooting

Check log:
```bash
cat /tmp/pilk_telegram_updates.log
```

Test manually:
```bash
cd /home/ubuntu/.openclaw/workspace/pilk-paper && python3 telegram_update.py
```

Need help? Reply with a command or message to trigger an immediate update.
