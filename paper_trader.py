import ccxt
import json
import os
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

console = Console()

# Configuration
INITIAL_BALANCE = 10000.0  # USDT
TAKER_FEE = 0.0005  # 0.05%
MAKER_FEE = 0.0002  # 0.02%
SAVE_FILE = "trade_log.json"

class PaperExchange:
    def __init__(self):
        self.exchange = ccxt.binanceusdm()
        # Load markets to get precision and limits
        try:
            self.exchange.load_markets()
        except Exception as e:
            console.print(f"[red]Error connecting to Binance Futures: {e}[/red]")

    def get_price(self, symbol):
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            console.print(f"[red]Error fetching price for {symbol}: {e}[/red]")
            return None

class Player:
    def __init__(self):
        self.balance = INITIAL_BALANCE
        self.positions = {}  # symbol -> {size, entry_price, type: 'long'/'short'}
        self.history = []
        self.load_state()

    def get_portfolio_value(self, current_prices):
        total_pnl = 0
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol)
            if price:
                pnl = self.calculate_pnl(symbol, price)
                total_pnl += pnl
        return self.balance + total_pnl

    def calculate_pnl(self, symbol, current_price):
        pos = self.positions.get(symbol)
        if not pos:
            return 0
        
        size = pos['size']
        entry_price = pos['entry_price']
        
        if pos['type'] == 'long':
            pnl = (current_price - entry_price) * size
        else:
            pnl = (entry_price - current_price) * size
            
        return pnl

    def execute_trade(self, symbol, side, amount_usdt, price, order_type='market'):
        # Fee calculation
        fee_rate = TAKER_FEE if order_type == 'market' else MAKER_FEE
        size = amount_usdt / price
        trade_value = size * price
        fee = trade_value * fee_rate
        
        # Verify balance for opening
        # Simplified margin check: assumes 1x leverage is affordable logic for 'balance'.
        # In futures, it's margin balance, but for this game we'll just check "Available Balance" roughly.
        # Closing positions credits PnL back to balance.
        
        # This is a simplified "netting" logic. 
        # If we have a position and trade same side -> Increase size (Avg Entry)
        # If we have a position and trade opposite side -> Reduce/Close (Realize Pnk)
        
        existing = self.positions.get(symbol)
        
        if existing:
            if existing['type'] == (side if side in ['long', 'short'] else ('long' if side == 'buy' else 'short')):
                 # Adding to position
                 # Logic for "Buy" on "Long" or "Sell" on "Short"
                 # Just treat 'buy' as long entry/cover short, 'sell' as short entry/close long? 
                 # Let's use strict: 'long' opens/adds long, 'short' opens/adds short.
                 # 'close' closes.
                 pass
            else:
                # Opposing logic is complex for simple script. 
                # Let's enforce: No hedging locally (One direction per symbol).
                pass

        # Let's stick to simple "Buy/Sell" (Long/Short) commands from user
        # User says: "long BTC/USDT 1000" -> Opens Long 1000 USDT worth
        # User says: "short BTC/USDT 1000" -> Opens Short 1000 USDT worth
        # User says: "close BTC/USDT" -> Closes entire position
        
        # 1. Deduct Fee
        self.balance -= fee
        
        if side == 'close':
            if not existing:
                console.print(f"[red]No position to close for {symbol}[/red]")
                return
            
            # Realize PnL
            pnl = self.calculate_pnl(symbol, price)
            self.balance += pnl
            
            # Log
            self.history.append({
                'time': datetime.now().isoformat(),
                'symbol': symbol,
                'action': 'CLOSE',
                'size': existing['size'],
                'price': price,
                'pnl': pnl,
                'fee': fee
            })
            del self.positions[symbol]
            console.print(f"[green]Closed {symbol}. PnL: {pnl:.2f} USDT. Fee: {fee:.2f} USDT[/green]")
            
        elif side in ['long', 'short']:
            # New Position or Add
            if existing:
                if existing['type'] != side:
                    console.print(f"[red]Cannot open {side} on {symbol}, you have a {existing['type']} position. Close it first.[/red]")
                    return
                # Averaging down/up
                total_size = existing['size'] + size
                avg_price = ((existing['size'] * existing['entry_price']) + (size * price)) / total_size
                existing['size'] = total_size
                existing['entry_price'] = avg_price
                console.print(f"[yellow]Added to {symbol} {side}. New Entry: {avg_price:.2f}[/yellow]")
            else:
                self.positions[symbol] = {
                    'type': side,
                    'size': size,
                    'entry_price': price,
                    'timestamp': datetime.now().isoformat()
                }
                console.print(f"[green]Opened {side} on {symbol} for {amount_usdt} USDT @ {price}[/green]")
            
            self.history.append({
                'time': datetime.now().isoformat(),
                'symbol': symbol,
                'action': side.upper(),
                'size': size,
                'price': price,
                'fee': fee
            })

        self.save_state()

    def save_state(self):
        data = {
            'balance': self.balance,
            'positions': self.positions,
            'history': self.history
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def load_state(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                self.balance = data.get('balance', INITIAL_BALANCE)
                self.positions = data.get('positions', {})
                self.history = data.get('history', [])

def display_dashboard(player, exchange):
    table = Table(title="Current Portfolio")
    table.add_column("Symbol", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Size", justify="right")
    table.add_column("Entry Price", justify="right")
    table.add_column("Mark Price", justify="right")
    table.add_column("PnL (USDT)", justify="right")
    table.add_column("ROE %", justify="right")

    current_prices = {}
    
    for symbol, pos in player.positions.items():
        price = exchange.get_price(symbol)
        if not price:
            continue
        current_prices[symbol] = price
        
        pnl = player.calculate_pnl(symbol, price)
        entry_val = pos['size'] * pos['entry_price']
        roe = (pnl / entry_val) * 100 if entry_val > 0 else 0
        
        pnl_color = "green" if pnl >= 0 else "red"
        
        table.add_row(
            symbol,
            pos['type'].upper(),
            f"{pos['size']:.4f}",
            f"{pos['entry_price']:.2f}",
            f"{price:.2f}",
            f"[{pnl_color}]{pnl:.2f}[/{pnl_color}]",
            f"[{pnl_color}]{roe:.2f}%[/{pnl_color}]"
        )

    # Summary
    console.print(table)
    
    # Calculate Total Portfolio Value
    portfolio_value = player.get_portfolio_value(current_prices)
    
    summary = Table.grid()
    summary.add_column()
    summary.add_column(justify="right")
    summary.add_row("Cash Balance:", f"{player.balance:.2f} USDT")
    summary.add_row("Equity:", f"{portfolio_value:.2f} USDT")
    
    pnl_total = portfolio_value - INITIAL_BALANCE
    color = "green" if pnl_total >= 0 else "red"
    summary.add_row("Total PnL:", f"[{color}]{pnl_total:.2f} USDT[/{color}]")
    
    console.print(Panel(summary, title="Account Summary"))

def main():
    console.print("[bold yellow]Welcome to Pilk Paper Trader (Binance Futures)[/bold yellow]")
    player = Player()
    exchange = PaperExchange()

    while True:
        try:
            command = Prompt.ask("\n[bold cyan]Command (long/short/close/status/history/quit)[/bold cyan]").strip().lower()
            
            if command in ['quit', 'exit']:
                break
                
            if command == 'status':
                with console.status("[bold green]Fetching market data..."):
                    display_dashboard(player, exchange)
                continue
                
            if command == 'history':
                table = Table(title="Trade History")
                table.add_column("Time", style="dim")
                table.add_column("Symbol")
                table.add_column("Action")
                table.add_column("Price")
                table.add_column("PnL")
                table.add_column("Fee")
                
                for trade in player.history:
                    pnl_str = f"{trade.get('pnl', 0):.2f}"
                    if trade.get('pnl', 0) > 0: pnl_str = f"[green]{pnl_str}[/green]"
                    elif trade.get('pnl', 0) < 0: pnl_str = f"[red]{pnl_str}[/red]"
                    
                    table.add_row(
                        trade['time'].split('T')[1][:8], # Time only
                        trade['symbol'],
                        trade['action'],
                        f"{trade['price']:.2f}",
                        pnl_str if 'pnl' in trade else "-",
                        f"{trade['fee']:.4f}"
                    )
                console.print(table)
                continue

            parts = command.split()
            if len(parts) < 2:
                console.print("[red]Invalid command format.[/red]")
                continue
            
            action = parts[0]
            # normalize symbol
            symbol = parts[1].upper()
            if '/' not in symbol:
                symbol += "/USDT" # default assumption
                
            if action == 'close':
                price = exchange.get_price(symbol)
                if price:
                    player.execute_trade(symbol, 'close', 0, price)
            elif action in ['long', 'short']:
                if len(parts) < 3:
                     console.print(f"[red]Usage: {action} <symbol> <USDT_Amount>[/red]")
                     continue
                try:
                    amount = float(parts[2])
                    price = exchange.get_price(symbol)
                    if price:
                        player.execute_trade(symbol, action, amount, price)
                except ValueError:
                    console.print("[red]Invalid amount[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
