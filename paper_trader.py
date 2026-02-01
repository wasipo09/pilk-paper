import ccxt
import json
import os
import time
import argparse
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

console = Console()

# Configuration
INITIAL_BALANCE = 1000.0  # USDT
TAKER_FEE = 0.0005  # 0.05%
MAKER_FEE = 0.0002  # 0.02%
SAVE_FILE = "trade_log.json"

class PaperExchange:
    def __init__(self):
        self.exchange = ccxt.binanceusdm()
        try:
            self.exchange.load_markets()
        except Exception as e:
            console.print(f"[red]Error connecting to Binance Futures: {e}[/red]")

    def get_price(self, symbol):
        # Try exact match first
        if symbol in self.exchange.markets:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                return ticker['last']
            except Exception as e:
                console.print(f"[red]Error fetching price for {symbol}: {e}[/red]")
                return None
        
        # Try appending :USDT for linear futures
        alt_symbol = f"{symbol}:USDT"
        if alt_symbol in self.exchange.markets:
            try:
                ticker = self.exchange.fetch_ticker(alt_symbol)
                return ticker['last']
            except Exception as e:
                console.print(f"[red]Error fetching price for {alt_symbol}: {e}[/red]")
                return None
        
        console.print(f"[red]Symbol {symbol} (or {alt_symbol}) not found in markets.[/red]")
        return None

class Player:
    def __init__(self, reset=False):
        self.balance = INITIAL_BALANCE
        self.positions = {}
        self.history = []
        if not reset:
            self.load_state()
        else:
            self.save_state()
            console.print(f"[green]New game started! Balance reset to {INITIAL_BALANCE} USDT.[/green]")

    def get_portfolio_value(self, current_prices):
        total_pnl = 0
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol)
            if price:
                pnl = self.calculate_pnl(symbol, price)
                # Check liquidation
                if pos['margin'] + pnl <= 0:
                     # Simulate liquidation value (0 margin left)
                     total_pnl -= pos['margin']
                else:
                     total_pnl += pnl
        # In isolated margin, your balance is separate from margin.
        # Equity = Wallet Balance + Sum(Margin + PnL)
        # But wait, Margin is ALREADY deducted from Balance when opening.
        # So Equity = Wallet Balance + Sum(Margin + Unreleased PnL)
        
        margin_equity = 0
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol)
            pnl = 0
            if price:
                 pnl = self.calculate_pnl(symbol, price)
            
            # If liquidated, equity for this pos is 0
            if pos['margin'] + pnl <= 0:
                margin_equity += 0
            else:
                margin_equity += (pos['margin'] + pnl)

        return self.balance + margin_equity

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

    def execute_trade(self, symbol, side, margin_usdt, leverage, price):
        # Validation
        if side in ['long', 'short']:
            if not (1 <= leverage <= 50):
                console.print("[red]Leverage must be between 1x and 50x[/red]")
                return
            
            if margin_usdt > self.balance:
                console.print(f"[red]Insufficient balance. Available: {self.balance:.2f} USDT[/red]")
                return

            if symbol in self.positions:
                console.print(f"[red]You already have a position in {symbol}. Averaging/Adding is not supported in this version. Close it first.[/red]")
                return

            # Open Position
            notional_value = margin_usdt * leverage
            size = notional_value / price
            
            # Taker Fee on Notional
            fee = notional_value * TAKER_FEE
            
            # Deduct Margin and Fee from Balance
            total_cost = margin_usdt + fee
            if total_cost > self.balance:
                 console.print(f"[red]Insufficient balance for Margin + Fee ({total_cost:.2f} USDT)[/red]")
                 return
                 
            self.balance -= total_cost
            
            # Estimated Liquidation Price
            # Long: Entry * (1 - 1/Lev) roughly? 
            # Exact: Bankruptcy Price => Entry - (Margin / Size) for Long
            #        Entry + (Margin / Size) for Short
            # (ignoring maintenance margin for simplicity, liq at bankruptcy)
            
            if side == 'long':
                liq_price = price - (margin_usdt / size)
            else:
                liq_price = price + (margin_usdt / size)

            self.positions[symbol] = {
                'type': side,
                'margin': margin_usdt,
                'leverage': leverage,
                'size': size,
                'entry_price': price,
                'liq_price': liq_price,
                'timestamp': datetime.now().isoformat()
            }
            
            console.print(f"[green]Opened {leverage}x {side} on {symbol}. Margin: {margin_usdt}, Size: {size:.4f}, Liq: {liq_price:.2f}[/green]")
            console.print(f"[dim]Fee deducted: {fee:.2f} USDT[/dim]")
            
            self.history.append({
                'time': datetime.now().isoformat(),
                'symbol': symbol,
                'action': f"OPEN {side.upper()} {leverage}x",
                'margin': margin_usdt,
                'price': price,
                'fee': fee
            })

        elif side == 'close':
            pos = self.positions.get(symbol)
            if not pos:
                console.print(f"[red]No position in {symbol}[/red]")
                return
            
            # Check if liquidated before closing?
            # Ideally done in status check, but let's calculate final value here
            pnl = self.calculate_pnl(symbol, price)
            
            # Liquidation check
            if pos['margin'] + pnl <= 0:
                console.print(f"[red]Position is LIQUIDATED! Loss: {pos['margin']:.2f} USDT[/red]")
                pnl = -pos['margin'] # Cap loss at margin
                return_amount = 0
            else:
                return_amount = pos['margin'] + pnl
            
            # Closing Fee (Taker)
            notional_value = pos['size'] * price
            close_fee = notional_value * TAKER_FEE
            
            final_payout = return_amount - close_fee
            
            self.balance += final_payout
            del self.positions[symbol]
            
            console.print(f"[green]Closed {symbol}. PnL: {pnl:.2f} USDT. Fee: {close_fee:.2f}. Returned: {final_payout:.2f}[/green]")
            
            self.history.append({
                'time': datetime.now().isoformat(),
                'symbol': symbol,
                'action': 'CLOSE',
                'price': price,
                'pnl': pnl,
                'fee': close_fee
            })

        self.save_state()

    def check_liquidations(self, exchange):
        # Helper to check passive liquidations
        to_remove = []
        for symbol, pos in self.positions.items():
            price = exchange.get_price(symbol)
            if not price: continue
            
            pnl = self.calculate_pnl(symbol, price)
            if pos['margin'] + pnl <= 0:
                console.print(f"[bold red]LIQUIDATION ALERT: {symbol} position wiped out![/bold red]")
                to_remove.append(symbol)
                
                self.history.append({
                    'time': datetime.now().isoformat(),
                    'symbol': symbol,
                    'action': 'LIQUIDATION',
                    'price': price,
                    'pnl': -pos['margin'],
                    'fee': 0
                })
        
        for s in to_remove:
            del self.positions[s]
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
    player.check_liquidations(exchange)
    
    table = Table(title=f"Current Portfolio - Balance: {player.balance:.2f} USDT")
    table.add_column("Symbol", style="cyan")
    table.add_column("Side/Lev", style="magenta")
    table.add_column("Margin", justify="right")
    table.add_column("Entry", justify="right")
    table.add_column("Mark", justify="right")
    table.add_column("Liq Price", style="red", justify="right")
    table.add_column("PnL (USDT)", justify="right")
    table.add_column("ROE %", justify="right")

    current_prices = {}
    
    for symbol, pos in player.positions.items():
        price = exchange.get_price(symbol)
        if not price:
            continue
        current_prices[symbol] = price
        
        pnl = player.calculate_pnl(symbol, price)
        roe = (pnl / pos['margin']) * 100
        
        pnl_color = "green" if pnl >= 0 else "red"
        
        table.add_row(
            symbol,
            f"{pos['type'].upper()} {pos['leverage']}x",
            f"{pos['margin']:.2f}",
            f"{pos['entry_price']:.2f}",
            f"{price:.2f}",
            f"{pos['liq_price']:.2f}",
            f"[{pnl_color}]{pnl:.2f}[/{pnl_color}]",
            f"[{pnl_color}]{roe:.2f}%[/{pnl_color}]"
        )

    console.print(table)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--new', action='store_true', help='Start a new game with reset portfolio')
    args = parser.parse_args()

    console.print("[bold yellow]Welcome to Pilk Paper Trader (Binance Futures)[/bold yellow]")
    
    if args.new:
        if os.path.exists(SAVE_FILE):
            os.rename(SAVE_FILE, f"{SAVE_FILE}.bak")
        player = Player(reset=True)
    else:
        player = Player(reset=False)
        
    exchange = PaperExchange()

    while True:
        try:
            command = Prompt.ask("\n[bold cyan]Command[/bold cyan]").strip().lower()
            
            if command in ['quit', 'exit']:
                break
                
            if command == 'status':
                with console.status("[bold green]Fetching market data..."):
                    display_dashboard(player, exchange)
                continue
                
            if command == 'history':
                # Quick history dump
                for h in player.history[-10:]:
                    console.print(h)
                continue

            parts = command.split()
            if not parts: continue
            
            action = parts[0]
            
            if action == 'close':
                if len(parts) < 2:
                    console.print("[red]Usage: close <symbol>[/red]")
                    continue
                symbol = parts[1].upper()
                # Symbol Correction
                if '/' not in symbol: symbol += "/USDT"
                
                price = exchange.get_price(symbol)
                if price:
                    player.execute_trade(symbol, 'close', 0, 0, price)
                    
            elif action in ['long', 'short']:
                if len(parts) < 4:
                     console.print(f"[red]Usage: {action} <symbol> <Margin_USDT> <Leverage>[/red]")
                     console.print("[dim]Example: long BTC/USDT 100 20 (Uses 100 USDT margin @ 20x)[/dim]")
                     continue
                try:
                    symbol = parts[1].upper()
                    if '/' not in symbol: symbol += "/USDT"
                    
                    margin = float(parts[2])
                    leverage = int(parts[3])
                    
                    price = exchange.get_price(symbol)
                    if price:
                        player.execute_trade(symbol, action, margin, leverage, price)
                except ValueError:
                    console.print("[red]Invalid numbers[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
