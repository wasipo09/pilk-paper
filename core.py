
import ccxt
import json
import os
import csv
from datetime import datetime

# Configuration (Shared)
INITIAL_BALANCE = 1000.0
TAKER_FEE = 0.0005
SAVE_FILE = "trade_log.json"
HISTORY_FILE = "history.csv"
MIN_EQUITY_GAME_OVER = 5.0

class TradeError(Exception):
    pass

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
            # In core we might just print or log, but for now we'll return empty
            print(f"Batch fetch failed: {e}") 
            return {}

import threading

class Player:
    def __init__(self, reset=False):
        self.balance = INITIAL_BALANCE
        self.positions = {}
        self.orders = []
        self.lock = threading.Lock()
        
        # load_state will handle partial loads
        if reset:
            self.save_state() # Reset file
            self.init_history_file()
            print(f"New game started! Balance reset to {INITIAL_BALANCE} USDT.")
        else:
            self.load_state()

    def init_history_file(self):
         with open(HISTORY_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Action", "Symbol", "Size", "Price", "Leverage", "Margin", "PnL", "Fee", "Balance_After"])

    def log_history(self, action, symbol, size, price, leverage, margin, pnl, fee):
        # Append to CSV
        file_exists = os.path.exists(HISTORY_FILE)
        
        # Ensure we don't crash if file is missing/deleted mid-game
        mode = 'a' if file_exists else 'w'
        
        with open(HISTORY_FILE, mode, newline='') as f:
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

    def update_portfolio(self, exchange, log_callback=None):
        """
        Updates portfolio equity, checks TP/SL, checks Liquidations, checks Limit Orders.
        log_callback: function(msg, style) to print to console if needed
        """
        def log(msg, style=""):
            if log_callback: log_callback(msg, style)
            else: print(msg)

        with self.lock:
            current_equity = self.balance
            
            # Collect symbols from Positions AND Orders
            feed_map = {} 
            for s, pos in self.positions.items():
                feed_sym = pos.get('feed_symbol', s)
                feed_map[feed_sym] = s
                
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
                    log(f"{trigger_reason} triggered for {user_sym} at {price:.2f}! PnL: {pnl:.2f}", "bold green")
                    fee = (pos['size'] * price) * TAKER_FEE
                    net_pnl = pnl - fee
                    self.balance += (pos['margin'] + net_pnl)
                    self.log_history(trigger_reason, user_sym, pos['size'], price, pos['leverage'], pos['margin'], pnl, fee)
                    positions_to_remove.append((user_sym, price, 0))
                    continue # Skip liquidation check

                # Liquidation Check
                if pos['margin'] + pnl <= 0:
                    log(f"LIQUIDATION ALERT: {user_sym} position wiped out! Price: {price}", "bold red")
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
            hit = False
            if order['type'] == 'long' and price <= order['limit_price']:
                hit = True
            elif order['type'] == 'short' and price >= order['limit_price']:
                hit = True
                
            if hit:
                log(f"LIMIT ORDER TRIGGERED: {order['type'].upper()} {order['symbol']} at {price:.2f}", "bold green")
                self.orders.remove(order)
                
                # We need to execute the trade now. 
                # Ideally execute_trade shouldn't depend on console printing too much.
                self.execute_trade(
                    order['symbol'], 
                    order['type'], 
                    order['margin'], 
                    order['leverage'], 
                    price, 
                    feed_symbol=fs,
                    tp=order.get('tp'),
                    sl=order.get('sl'),
                    log_callback=log_callback
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
        
    def place_limit_order(self, symbol, side, price, margin, leverage, feed_symbol=None, tp=None, sl=None, log_callback=None):
         def log(msg, style=""):
            if log_callback: log_callback(msg, style)
            else: print(msg)

         if margin <= 0:
            raise TradeError("Margin must be positive.")

         with self.lock:
             if margin > self.balance:
                raise TradeError("Insufficient balance to lock for order.")
                
             self.orders.append({
                 'symbol': symbol,
                 'side': side, 
                 'type': side, 
                 'limit_price': price,
                 'margin': margin,
                 'leverage': leverage,
                 'feed_symbol': feed_symbol or symbol,
                 'tp': tp,
                 'sl': sl,
                 'timestamp': datetime.now().isoformat()
             })
             log(f"Limit Order Placed: {side.upper()} {symbol} @ {price:.2f}", "yellow")
             self.save_state()

    def execute_trade(self, symbol, side, margin, leverage, price, feed_symbol=None, tp=None, sl=None, log_callback=None):
        def log(msg, style=""):
            if log_callback: log_callback(msg, style)
            else: print(msg)

        if side in ['long', 'short']:
            # Limits
            if not (1 <= leverage <= 50):
                raise TradeError("Leverage must be 1-50x")
            
            if margin <= 0:
                raise TradeError("Margin must be positive.")

            if price <= 0:
                raise TradeError("Invalid price (<= 0).")

            with self.lock:
                if margin > self.balance:
                    raise TradeError(f"Insufficient balance. Available: {self.balance:.2f}")
                
                if symbol in self.positions:
                    raise TradeError(f"Already have position in {symbol}. Close first.")

                notional = margin * leverage
                size = notional / price
                fee = notional * TAKER_FEE
                
                total_cost = margin + fee
                if total_cost > self.balance:
                     raise TradeError(f"Cost ({total_cost:.2f}) exceeds balance.")
                     
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
                
                log(f"Opened {side.upper()} {symbol}. Size: {size:.4f}, Liq: {liq_price:.2f}{extras}", "green")
                self.log_history(f"OPEN_{side.upper()}", symbol, size, price, leverage, margin, 0, fee)
                self.save_state()
            
        elif side == 'close':
            with self.lock:
                pos = self.positions.get(symbol)
                if not pos:
                    raise TradeError(f"No position in {symbol}")
                    
                pnl = self.calculate_pnl(symbol, price)
                fee = (pos['size'] * price) * TAKER_FEE
                net_pnl = pnl - fee
                
                self.balance += (pos['margin'] + net_pnl)
                
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
