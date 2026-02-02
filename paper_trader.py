import ccxt
import json
import os
import csv
import argparse
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()

from core import PaperExchange, Player, INITIAL_BALANCE, MIN_EQUITY_GAME_OVER, SAVE_FILE, HISTORY_FILE, TradeError

def display_status(player, exchange):
    # Collect feed symbols
    feed_map = {} 
    for s, pos in player.positions.items():
        feed_sym = pos.get('feed_symbol', s)
        feed_map[feed_sym] = s
    
    # Batch fetch
    with console.status("[cyan]Fetching prices...[/cyan]"):
        prices = exchange.get_prices(list(feed_map.keys()))

    table = Table(title=f"Portfolio (Bal: {player.balance:.2f} USDT)")
    table.add_column("Symbol")
    table.add_column("Side")
    table.add_column("Margin")
    table.add_column("Ent. Price")
    table.add_column("Mark Price")
    table.add_column("Liq Price", style="red")
    table.add_column("PnL")
    
    current_equity = player.balance
    
    for feed_sym, user_sym in feed_map.items():
        pos = player.positions[user_sym]
        price = prices.get(feed_sym)
        
        if not price:
            current_equity += pos['margin']
            continue
            
        pnl = player.calculate_pnl_raw(pos, price)
        current_equity += (pos['margin'] + pnl)
        
        roe = (pnl / pos['margin']) * 100
        color = "green" if pnl >= 0 else "red"
        
        extras = ""
        if pos.get('tp') or pos.get('sl'):
             extras = f"\nTP:{pos.get('tp')} SL:{pos.get('sl')}"
        
        table.add_row(
            user_sym + extras,
            f"{pos['type'].upper()} {pos['leverage']}x",
            f"{pos['margin']:.2f}",
            f"{pos['entry_price']:.2f}",
            f"{price:.2f}",
            f"{pos['liq_price']:.2f}",
            f"[{color}]{pnl:.2f} ({roe:.0f}%)[/{color}]"
        )
        
    console.print(table)
    console.print(f"Total Equity: [bold]{current_equity:.2f} USDT[/bold]")
    
    if player.orders:
        otable = Table(title="Open Limit Orders")
        otable.add_column("Type")
        otable.add_column("Symbol")
        otable.add_column("Trigger Price")
        otable.add_column("Margin")
        for o in player.orders:
            otable.add_row(
                o['type'].upper(),
                o['symbol'],
                f"{o['limit_price']}",
                f"{o['margin']} ({o['leverage']}x)"
            )
        console.print(otable)

def print_history():
    if not os.path.exists(HISTORY_FILE):
        console.print("[yellow]No history yet.[/yellow]")
        return
        
    table = Table(title="Trade History")
    table.add_column("Time")
    table.add_column("Action")
    table.add_column("Symbol")
    table.add_column("PnL")
    table.add_column("Bal After")
    
    with open(HISTORY_FILE, 'r') as f:
        reader = csv.reader(f)
        try:
            next(reader, None) # header
            rows = list(reader)
            for row in rows[-15:]: # Last 15
                 pnl = float(row[7])
                 color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
                 table.add_row(
                     row[0].split('T')[1][:8],
                     row[1],
                     row[2],
                     f"[{color}]{pnl:.2f}[/{color}]",
                     f"{float(row[9]):.2f}"
                 )
        except Exception:
            pass
            
    console.print(table)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--new', action='store_true', help="Start new game")
    parser.add_argument('--start', action='store_true', help="Start new game (alias for --new)")
    args = parser.parse_args()

    console.print("[bold yellow]Pilk Paper Trader v2.0[/bold yellow]")
    
    if args.new or args.start:
        if os.path.exists(SAVE_FILE):
            os.rename(SAVE_FILE, f"{SAVE_FILE}.bak")
        player = Player(reset=True)
    else:
        player = Player()
    
    exchange = PaperExchange()

    while True:
        # GLOBAL UPDATE
        with console.status("[cyan]Updating markets...[/cyan]", spinner="dots"):
             def log_adapter(msg, style=""):
                 if style:
                     console.print(f"[{style}]{msg}[/{style}]")
                 else:
                     console.print(msg)

             equity = player.update_portfolio(exchange, log_callback=log_adapter)
             
        if equity < MIN_EQUITY_GAME_OVER:
            console.print(Panel(f"[bold red]GAME OVER[/bold red]\n\nYour equity ({equity:.2f} USDT) has dropped below 5 USDT.\n\nUse --new to restart."))
            sys.exit(0)

        try:
            cmd = Prompt.ask(f"\n[cyan]Command ({equity:.0f} Eq)[/cyan]").strip().lower()
            if cmd in ['quit', 'exit']: break
            
            parts = cmd.split()
            if not parts: continue
            
            # Shortcuts
            aliases = {
                'b': 'long', 'buy': 'long',
                's': 'short', 'sell': 'short',
                'c': 'close',
                'st': 'status',
                'h': 'history',
                'limit': 'limit'
            }
            
            action = aliases.get(parts[0], parts[0])
            
            if action == 'close':
                if len(parts) < 2:
                    console.print("[red]Usage: c <SYM>[/red]")
                    continue
                symbol = parts[1].upper()
                if '/' not in symbol: symbol += "/USDT"
                
                with console.status("Fetching price..."):
                    feed_sym, price = exchange.resolve_symbol_and_price(symbol)
                
                if price:
                    try:
                        player.execute_trade(symbol, 'close', 0, 0, price, log_callback=log_adapter)
                    except TradeError as e:
                        console.print(f"[red]{e}[/red]")
                else: 
                     console.print("[red]Price fetch failed or symbol invalid.[/red]")
            
            elif action == 'limit':
                 # limit <type> <sym> <price> <margin> <lev>
                 if len(parts) < 6:
                     console.print("[red]Usage: limit <long/short> <sym> <price> <margin> <lev>[/red]")
                     continue
                 try:
                     side = parts[1].lower()
                     if side not in ['long', 'short']:
                         console.print("[red]Type must be long or short[/red]")
                         continue
                         
                     symbol = parts[2].upper()
                     if '/' not in symbol: symbol += "/USDT"
                     
                     limit_price = float(parts[3])
                     margin = float(parts[4])
                     lev = int(parts[5])
                     
                     with console.status("Checking symbol..."):
                         feed_sym, curr_price = exchange.resolve_symbol_and_price(symbol)
                         
                     if not feed_sym:
                         console.print("[red]Symbol not found[/red]")
                         continue
                         
                     try:
                         player.place_limit_order(symbol, side, limit_price, margin, lev, feed_symbol=feed_sym, log_callback=log_adapter)
                     except TradeError as e:
                         console.print(f"[red]{e}[/red]")
                     
                 except ValueError:
                     console.print("[red]Invalid numbers[/red]")
                    
            elif action in ['long', 'short']:
                # Parse optional flags manually
                # Syntax: cmd <sym> <margin> <lev> [--tp X] [--sl Y]
                try:
                    if len(parts) < 4:
                         # Check if user forgot args, unless they are typing 'b' alone?
                         raise IndexError
                         
                    # Basic args
                    symbol = parts[1].upper()
                    if '/' not in symbol: symbol += "/USDT"
                    margin = float(parts[2])
                    lev = int(parts[3])
                    
                    # Optional flags
                    tp = None
                    sl = None
                    
                    if '--tp' in parts:
                        tp_idx = parts.index('--tp') + 1
                        if tp_idx < len(parts): tp = float(parts[tp_idx])
                    if '--sl' in parts:
                        sl_idx = parts.index('--sl') + 1
                        if sl_idx < len(parts): sl = float(parts[sl_idx])

                    with console.status("Fetching price..."):
                        feed_sym, price = exchange.resolve_symbol_and_price(symbol)
                    
                    if price:
                        try:
                            player.execute_trade(symbol, action, margin, lev, price, feed_symbol=feed_sym, tp=tp, sl=sl, log_callback=log_adapter)
                        except TradeError as e:
                            console.print(f"[red]{e}[/red]")
                    else:
                        console.print("[red]Symbol not found or Error.[/red]")
                except (ValueError, IndexError):
                    console.print("[red]Usage: b/s <SYM> <MARGIN> <LEV> [--tp PRICE] [--sl PRICE][/red]")
            
            elif action == 'status':
                display_status(player, exchange)
            elif action == 'history':
                print_history()
            else:
                console.print(f"[red]Unknown command: {action}[/red]")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
