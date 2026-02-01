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
from rich.status import Status

console = Console()

# Configuration
INITIAL_BALANCE = 1000.0
TAKER_FEE = 0.0005
MAKER_FEE = 0.0002
SAVE_FILE = "trade_log.json"
HISTORY_FILE = "history.csv"
MIN_EQUITY_GAME_OVER = 5.0

class PaperExchange:
    def __init__(self):
        self.exchange = ccxt.binanceusdm()
        try:
            self.exchange.load_markets()
        except Exception:
            # Silent fail on init, retry in usage
            pass

    def resolve_symbol_and_price(self, symbol):
        # Returns (feed_symbol, price) or (None, None)
        # 1. Try exact
        if symbol in self.exchange.markets:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                return symbol, ticker['last']
            except: pass
            
        # 2. Try :USDT
        alt = f"{symbol}:USDT"
        if alt in self.exchange.markets:
             try:
                ticker = self.exchange.fetch_ticker(alt)
                return alt, ticker['last']
             except: pass
        
        return None, None

    def get_price(self, symbol):
        # Legacy single fetch (for close/open checks)
        sym, price = self.resolve_symbol_and_price(symbol)
        return price

    def get_prices(self, symbols):
        # Batch fetch
        if not symbols: return {}
        try:
            tickers = self.exchange.fetch_tickers(symbols)
            return {s: t['last'] for s, t in tickers.items()}
        except Exception as e:
            console.print(f"[red]Batch fetch failed: {e}[/red]")
            return {}

class Player:
    def __init__(self, reset=False):
        self.balance = INITIAL_BALANCE
        self.positions = {}
        # load_state will handle partial loads
        if reset:
            self.save_state() # Reset file
            self.init_history_file()
            console.print(f"[green]New game started! Balance reset to {INITIAL_BALANCE} USDT.[/green]")
        else:
            self.load_state()

    def init_history_file(self):
         with open(HISTORY_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Action", "Symbol", "Size", "Price", "Leverage", "Margin", "PnL", "Fee", "Balance_After"])

    def log_history(self, action, symbol, size, price, leverage, margin, pnl, fee):
        # Append to CSV
        file_exists = os.path.exists(HISTORY_FILE)
        with open(HISTORY_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Action", "Symbol", "Size", "Price", "Leverage", "Margin", "PnL", "Fee", "Balance_After"])
            
            writer.writerow([
                datetime.now().isoformat(),
                action,
                symbol,
                size,
                price,
                leverage,
                margin,
                pnl,
                fee,
                self.balance
            ])

    def update_portfolio(self, exchange):
        current_equity = self.balance
        if not self.positions:
            return current_equity

        # Batch Fetch
        # Collect all feed_symbols
        # Note: self.positions keys are typically user-friendly names, 
        # but we should store the real 'feed_symbol' inside the position dict for updates
        
        feed_map = {} # feed_symbol -> user_symbol
        for s, pos in self.positions.items():
            feed_sym = pos.get('feed_symbol', s) # Fallback to key if missing
            feed_map[feed_sym] = s
            
        prices = exchange.get_prices(list(feed_map.keys()))
        
        positions_to_remove = []

        for feed_sym, user_sym in feed_map.items():
            pos = self.positions[user_sym]
            price = prices.get(feed_sym)
            
            if not price:
                current_equity += pos['margin']
                continue
                
            pnl = self.calculate_pnl_raw(pos, price)
            
            if pos['margin'] + pnl <= 0:
                console.print(f"[bold red]LIQUIDATION ALERT: {user_sym} position wiped out! Price: {price}[/bold red]")
                positions_to_remove.append((user_sym, price, -pos['margin']))
            else:
                current_equity += (pos['margin'] + pnl)

        for sym, price, loss in positions_to_remove:
            pos = self.positions[sym]
            self.log_history('LIQUIDATION', sym, pos['size'], price, pos['leverage'], pos['margin'], loss, 0)
            del self.positions[sym]
        
        self.save_state()
        return current_equity

    def calculate_pnl_raw(self, pos, current_price):
        size = pos['size']
        entry_price = pos['entry_price']
        if pos['type'] == 'long':
            return (current_price - entry_price) * size
        else:
            return (entry_price - current_price) * size

    def calculate_pnl(self, symbol, current_price):
        pos = self.positions.get(symbol)
        if not pos: return 0
        return self.calculate_pnl_raw(pos, current_price)

    def execute_trade(self, symbol, side, margin, leverage, price, feed_symbol=None):
        if side in ['long', 'short']:
            # Limits
            if not (1 <= leverage <= 50):
                console.print("[red]Leverage must be 1-50x[/red]")
                return
            
            if margin > self.balance:
                console.print(f"[red]Insufficient balance. Available: {self.balance:.2f}[/red]")
                return
            
            if symbol in self.positions:
                console.print(f"[red]Already have position in {symbol}. Close first.[/red]")
                return

            notional = margin * leverage
            size = notional / price
            fee = notional * TAKER_FEE
            
            total_cost = margin + fee
            if total_cost > self.balance:
                 console.print(f"[red]Cost ({total_cost:.2f}) exceeds balance.[/red]")
                 return
                 
            self.balance -= total_cost
            
            # Liq Price calculation
            if side == 'long':
                liq_price = price - (margin / size)
            else:
                liq_price = price + (margin / size)

            self.positions[symbol] = {
                'type': side,
                'margin': margin,
                'leverage': leverage,
                'size': size,
                'entry_price': price,
                'liq_price': liq_price,
                'feed_symbol': feed_symbol or symbol,
                'timestamp': datetime.now().isoformat()
            }
            
            console.print(f"[green]Opened {side.upper()} {symbol}. Size: {size:.4f}, Liq: {liq_price:.2f}[/green]")
            self.log_history(f"OPEN_{side.upper()}", symbol, size, price, leverage, margin, 0, fee)
            
        elif side == 'close':
            pos = self.positions.get(symbol)
            if not pos:
                console.print(f"[red]No position in {symbol}[/red]")
                return
                
            pnl = self.calculate_pnl(symbol, price)
            
            # Check    # Remove check_liquidations method from Player as it's done in update_portfolio
    # But for display_status we need similar batch logic, or just rely on passing prices.
            self.log_history("CLOSE", symbol, pos['size'], price, pos['leverage'], pos['margin'], pnl, fee)
            del self.positions[symbol]

        self.save_state()

    def save_state(self):
        data = {
            'balance': self.balance,
            'positions': self.positions
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_state(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                self.balance = data.get('balance', INITIAL_BALANCE)
                self.positions = data.get('positions', {})
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
        
        table.add_row(
            user_sym,
            f"{pos['type'].upper()} {pos['leverage']}x",
            f"{pos['margin']:.2f}",
            f"{pos['entry_price']:.2f}",
            f"{price:.2f}",
            f"{pos['liq_price']:.2f}",
            f"[{color}]{pnl:.2f} ({roe:.0f}%)[/{color}]"
        )
        
    console.print(table)
    console.print(f"Total Equity: [bold]{current_equity:.2f} USDT[/bold]")

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
             equity = player.update_portfolio(exchange)
             
        if equity < MIN_EQUITY_GAME_OVER:
            console.print(Panel(f"[bold red]GAME OVER[/bold red]\n\nYour equity ({equity:.2f} USDT) has dropped below 5 USDT.\n\nUse --new to restart."))
            sys.exit(0)

        try:
            cmd = Prompt.ask(f"\n[cyan]Command ({equity:.0f} Eq)[/cyan]").strip().lower()
            if cmd in ['quit', 'exit']: break
            
            if cmd == 'status':
                display_status(player, exchange)
                continue
            if cmd == 'history':
                print_history()
                continue
                
            parts = cmd.split()
            if not parts: continue
            
            action = parts[0]
            
            if action == 'close':
                if len(parts) < 2:
                    console.print("[red]Usage: close <SYM>[/red]")
                    continue
                symbol = parts[1].upper()
                if '/' not in symbol: symbol += "/USDT"
                
                # Fetch fresh price
                with console.status("Fetching price..."):
                    # Use resolve logic if possible, or simple get_price for now (legacy method in class)
                    # Use get_prices for batch?
                    # Let's use the robust resolve we added
                    feed_sym, price = exchange.resolve_symbol_and_price(symbol)
                
                if price:
                    # We pass feed_sym? Close checks position keys anyway. 
                    # If position key matches user symbol, we are good.
                    player.execute_trade(symbol, 'close', 0, 0, price)
                else: 
                     console.print("[red]Price fetch failed or symbol invalid.[/red]")
                    
            elif action in ['long', 'short']:
                if len(parts) < 4:
                    console.print("[red]Usage: long/short <SYM> <MARGIN> <LEV>[/red]")
                    continue
                try:
                    symbol = parts[1].upper()
                    if '/' not in symbol: symbol += "/USDT"
                    margin = float(parts[2])
                    lev = int(parts[3])
                    
                    with console.status("Fetching price..."):
                        feed_sym, price = exchange.resolve_symbol_and_price(symbol)
                    
                    if price:
                        player.execute_trade(symbol, action, margin, lev, price, feed_symbol=feed_sym)
                    else:
                        console.print("[red]Symbol not found or Error.[/red]")
                except ValueError:
                    console.print("[red]Invalid numbers[/red]")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
