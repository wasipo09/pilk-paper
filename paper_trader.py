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
        self.orders = []
        # load_state will handle partial loads
        if reset:
            self.save_state() # Reset file
            self.init_history_file()
            console.print(f"[green]New game started! Balance reset to {INITIAL_BALANCE} USDT.[/green]")
        else:
            self.load_state()

    def save_state(self):
        data = {
            'balance': self.balance,
            'positions': self.positions,
            'orders': self.orders
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_state(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                self.balance = data.get('balance', INITIAL_BALANCE)
                self.positions = data.get('positions', {})
                self.orders = data.get('orders', [])

# ... [methods]

def display_status(player, exchange):
    # Collect feed symbols
    feed_map = {} 
    for s, pos in player.positions.items():
        feed_sym = pos.get('feed_symbol', s)
        feed_map[feed_sym] = s
    
    # Add orders to feed map?
    # No, we just show them separate, but let's keep it simple.
        
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
        

# ... [print_history] ...

def main():
    # ... [args] ...
    # ... [init] ...
    # ... [main loop] ...
            
            action = aliases.get(parts[0], parts[0])
            
            # ... [close] ...
            
            if action == 'limit':
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
                     
                     # Resolve symbol to get feed_symbol, but don't strictly need current price
                     # But good to check it exists
                     with console.status("Checking symbol..."):
                         feed_sym, curr_price = exchange.resolve_symbol_and_price(symbol)
                         
                     if not feed_sym:
                         console.print("[red]Symbol not found[/red]")
                         continue
                         
                     player.place_limit_order(symbol, side, limit_price, margin, lev, feed_symbol=feed_sym)
                     
                 except ValueError:
                     console.print("[red]Invalid numbers[/red]")
            
            elif action in ['long', 'short']:
                 # ... [existing logic] ...
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

        for sym, price, loss in positions_to_remove:
            if sym in self.positions:
                if loss < 0:
                     pos = self.positions[sym]
                     self.log_history('LIQUIDATION', sym, pos['size'], price, pos['leverage'], pos['margin'], loss, 0)
                del self.positions[sym]
        
        # 3. Check Limit Orders
        # We need to iterate over a copy because we might modify the list
        orders_executed = []
        for i, order in enumerate(list(self.orders)):
            sym = order['symbol']
            # We need price for this symbol.
            # If we don't have it in positions, it might not be in prices map.
            # We should probably pass a superset of symbols to get_prices, or separate fetch?
            # For efficiency in this simple game, we only check orders for symbols we already fetched,
            # OR we fetch specifically for orders if missing.
            # To capture all, let's fetch any missing order symbols.
            pass 
        
        # RETHINK: We need prices for ALL orders too. 
        # Let's do a second fetch or combine them at start of update_portfolio?
        # Combining is better.
        
        self.save_state()
        return current_equity

    def update_portfolio(self, exchange):
        current_equity = self.balance
        
        # Collect symbols from Positions AND Orders
        feed_map = {} 
        for s, pos in self.positions.items():
            feed_sym = pos.get('feed_symbol', s)
            feed_map[feed_sym] = s
            
        order_map = {} # feed_sym -> list of indices or objects
        for order in self.orders:
             # Orders store 'symbol' and 'feed_symbol'
             fs = order.get('feed_symbol', order['symbol'])
             feed_map[fs] = order['symbol'] # Matches user symbol

        # Batch Fetch
        if not feed_map:
             return current_equity

        prices = exchange.get_prices(list(feed_map.keys()))
        
        positions_to_remove = []

        # 1. Update Positions
        for feed_sym, user_sym in feed_map.items():
            price = prices.get(feed_sym)
            if not price: continue
            
            # If it's a position
            if user_sym in self.positions:
                pos = self.positions[user_sym]
                
                # ... [PnL Calculation] ...
                pnl = self.calculate_pnl_raw(pos, price)
                
                # TP/SL Checks
                triggered = False
                trigger_reason = ""
                
                if pos.get('tp'):
                    if (pos['type'] == 'long' and price >= pos['tp']) or \
                       (pos['type'] == 'short' and price <= pos['tp']):
                        triggered = True
                        trigger_reason = "TAKE_PROFIT"
                
                if not triggered and pos.get('sl'):
                    if (pos['type'] == 'long' and price <= pos['sl']) or \
                       (pos['type'] == 'short' and price >= pos['sl']):
                        triggered = True
                        trigger_reason = "STOP_LOSS"
                
                if triggered:
                    console.print(f"[bold green]{trigger_reason} triggered for {user_sym} at {price:.2f}! PnL: {pnl:.2f}[/bold green]")
                    fee = (pos['size'] * price) * TAKER_FEE
                    net_pnl = pnl - fee
                    self.balance += (pos['margin'] + net_pnl)
                    self.log_history(trigger_reason, user_sym, pos['size'], price, pos['leverage'], pos['margin'], pnl, fee)
                    positions_to_remove.append((user_sym, price, 0))
                    continue # Skip liquidation check

                # Liquidation Check
                if pos['margin'] + pnl <= 0:
                    console.print(f"[bold red]LIQUIDATION ALERT: {user_sym} position wiped out! Price: {price}[/bold red]")
                    positions_to_remove.append((user_sym, price, -pos['margin']))
                else:
                    current_equity += (pos['margin'] + pnl)

        # Remove triggered/liquidated positions
        for sym, price, loss in positions_to_remove:
             if sym in self.positions:
                if loss < 0:
                     pos = self.positions[sym]
                     self.log_history('LIQUIDATION', sym, pos['size'], price, pos['leverage'], pos['margin'], loss, 0)
                del self.positions[sym]

        # 2. Check Limit Orders
        for order in list(self.orders):
            fs = order.get('feed_symbol', order['symbol'])
            price = prices.get(fs)
            if not price: continue
            
            # Check condition
            # Limit Long: Buy if price <= limit_price
            # Limit Short: Sell if price >= limit_price
            hit = False
            if order['type'] == 'long' and price <= order['limit_price']:
                hit = True
            elif order['type'] == 'short' and price >= order['limit_price']:
                hit = True
                
            if hit:
                console.print(f"[bold green]LIMIT ORDER TRIGGERED: {order['type'].upper()} {order['symbol']} at {price:.2f}[/bold green]")
                # Execute Trade
                # Note: We need to check if we already have a position in this symbol?
                # The execute_trade method checks that.
                
                # Remove order first to prevent loop if execute fails? 
                # Or keep if fail? Let's remove.
                self.orders.remove(order)
                
                self.execute_trade(
                    order['symbol'], 
                    order['type'], 
                    order['margin'], 
                    order['leverage'], 
                    price, # Fill at current price (which is better or equal to limit)
                    feed_symbol=fs,
                    tp=order.get('tp'),
                    sl=order.get('sl')
                )

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
        
    def place_limit_order(self, symbol, side, price, margin, leverage, feed_symbol=None, tp=None, sl=None):
         if margin > self.balance:
            console.print(f"[red]Insufficient balance to lock for order.[/red]")
            return
            
         # We do NOT lock balance for orders in this simple version, 
         # or we SHOULD? Realism says yes. 
         # Let's separate 'available balance' vs 'equity'.
         # For simplicity: Check balance at execution time. (Binance does this for some modes).
         # User asked for 'realistic', but simple. Let's not lock yet to avoid complex 'in_order' accounting.
         # Actually, logging it is enough.
         
         self.orders.append({
             'symbol': symbol,
             'side': side, # Wait, execute_trade uses 'side' but I used 'type' in check. Normalize.
             'type': side, 
             'limit_price': price,
             'margin': margin,
             'leverage': leverage,
             'feed_symbol': feed_symbol or symbol,
             'tp': tp,
             'sl': sl,
             'timestamp': datetime.now().isoformat()
         })
         console.print(f"[yellow]Limit Order Placed: {side.upper()} {symbol} @ {price:.2f}[/yellow]")
         self.save_state()

    def execute_trade(self, symbol, side, margin, leverage, price, feed_symbol=None, tp=None, sl=None):
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
                'timestamp': datetime.now().isoformat(),
                'tp': tp,
                'sl': sl
            }
            
            extras = ""
            if tp: extras += f" TP: {tp}"
            if sl: extras += f" SL: {sl}"
            
            console.print(f"[green]Opened {side.upper()} {symbol}. Size: {size:.4f}, Liq: {liq_price:.2f}{extras}[/green]")
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
            'positions': self.positions,
            'orders': self.orders
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_state(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                self.balance = data.get('balance', INITIAL_BALANCE)
                self.positions = data.get('positions', {})
                self.orders = data.get('orders', [])
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
            
            # Shortcuts
            aliases = {
                'b': 'long', 'buy': 'long',
                's': 'short', 'sell': 'short',
                'c': 'close',
                'st': 'status',
                'h': 'history',
                'limit': 'limit' # Future preparation
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
                    player.execute_trade(symbol, 'close', 0, 0, price)
                else: 
                     console.print("[red]Price fetch failed or symbol invalid.[/red]")
                    
            elif action in ['long', 'short']:
                # Parse optional flags manually
                # Syntax: cmd <sym> <margin> <lev> [--tp X] [--sl Y]
                try:
                    # Basic args
                    symbol = parts[1].upper()
                    if '/' not in symbol: symbol += "/USDT"
                    margin = float(parts[2])
                    lev = int(parts[3])
                    
                    # Optional flags
                    tp = None
                    sl = None
                    
                    # Basic parser for --tp and --sl
                    if '--tp' in parts:
                        tp_idx = parts.index('--tp') + 1
                        if tp_idx < len(parts): tp = float(parts[tp_idx])
                    if '--sl' in parts:
                        sl_idx = parts.index('--sl') + 1
                        if sl_idx < len(parts): sl = float(parts[sl_idx])

                    with console.status("Fetching price..."):
                        feed_sym, price = exchange.resolve_symbol_and_price(symbol)
                    
                    if price:
                        player.execute_trade(symbol, action, margin, lev, price, feed_symbol=feed_sym, tp=tp, sl=sl)
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
