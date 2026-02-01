import unittest
from unittest.mock import MagicMock, patch
import os
import json
import csv
import paper_trader

class TestPaperTrader(unittest.TestCase):

    def setUp(self):
        # Setup temp files
        self.save_file = "test_trade_log.json"
        self.history_file = "test_history.csv"
        paper_trader.SAVE_FILE = self.save_file
        paper_trader.HISTORY_FILE = self.history_file
        
        # Reset Player
        self.player = paper_trader.Player(reset=True)
        self.exchange = MagicMock()

    def tearDown(self):
        # Cleanup
        if os.path.exists(self.save_file): os.remove(self.save_file)
        if os.path.exists(self.history_file): os.remove(self.history_file)
    
    def test_initialization(self):
        self.assertEqual(self.player.balance, 1000.0)
        self.assertTrue(os.path.exists(self.history_file))

    def test_open_position_valid(self):
        # Mock price
        price = 50000.0
        margin = 100.0
        lev = 10
        
        # Fee: 1000 notional * 0.0005 = 0.5
        # Total deduction: 100 + 0.5 = 100.5
        
        self.player.execute_trade("BTC/USDT", "long", margin, lev, price)
        
        self.assertIn("BTC/USDT", self.player.positions)
        pos = self.player.positions["BTC/USDT"]
        self.assertEqual(pos['size'], 0.02) # 1000 / 50000
        self.assertEqual(self.player.balance, 1000.0 - 100.5)

    def test_pnl_calculation(self):
        price = 100.0
        self.player.execute_trade("SOL/USDT", "long", 100, 1, price) 
        # Size = 1.0 SOL. 
        # Price goes to 110. PnL should be (110-100)*1 = 10.
        
        new_price = 110.0
        pnl = self.player.calculate_pnl("SOL/USDT", new_price)
        self.assertAlmostEqual(pnl, 10.0)

    def test_liquidation(self):
        price = 100.0
        margin = 10.0
        lev = 10
        # Notional 100. Size 1.0. 
        # Long. Liq if PnL <= -10. 
        # PnL = (Curr - Entry) * Size
        # -10 = (Curr - 100) * 1  => Curr = 90.
        
        self.player.execute_trade("LUNA/USDT", "long", margin, lev, price)
        
        # Mock exchange to return liquidation price via get_prices
        # Note: Player stores the symbol as key, but might use feed_symbol.
        # In test, feed_symbol defaults to symbol if not from resolve.
        self.exchange.get_prices.return_value = {"LUNA/USDT": 89.0}
        
        # Update Portfolio
        self.player.update_portfolio(self.exchange)
        
        self.assertNotIn("LUNA/USDT", self.player.positions)
        # Check history for LIQUIDATION
        with open(self.history_file, 'r') as f:
            content = f.read()
            self.assertIn("LIQUIDATION", content)

    def test_game_over_logic(self):
        # Manually drain balance
        self.player.balance = 4.0
        self.player.save_state()
        
        # Update portfolio should return equity
        # Return empty dict for prices so no change in val
        self.exchange.get_prices.return_value = {}
        
        equity = self.player.update_portfolio(self.exchange)
        self.assertEqual(equity, 4.0)
        self.assertTrue(equity < paper_trader.MIN_EQUITY_GAME_OVER)

    def test_tp_trigger(self):
        # Long BTC at 50000. TP 51000.
        price = 50000.0
        self.player.execute_trade("BTC/USDT", "long", 100, 10, price, tp=51000.0)
        
        # Move price to 51001 (trigger TP)
        self.exchange.get_prices.return_value = {"BTC/USDT": 51001.0}
        
        current_bal = self.player.balance # Balance after entry (fee ded.)
        
        self.player.update_portfolio(self.exchange)
        
        # Position should be gone
        self.assertNotIn("BTC/USDT", self.player.positions)
        
        # Balance should be higher than at start (profit)
        # 100 margin + profit. Profit approx (1001 diff * 0.02 size) - close fee
        self.assertTrue(self.player.balance > current_bal + 100)

        # Check history
        with open(self.history_file, 'r') as f:
            self.assertIn("TAKE_PROFIT", f.read())

    def test_sl_trigger(self):
        # Long at 50000. SL 49000.
        price = 50000.0
        self.player.execute_trade("ETH/USDT", "long", 100, 10, price, sl=49000.0)
        
        # Move price to 48999
        self.exchange.get_prices.return_value = {"ETH/USDT": 48999.0}
        
        self.player.update_portfolio(self.exchange)
        
        self.assertNotIn("ETH/USDT", self.player.positions)
        
        with open(self.history_file, 'r') as f:
            self.assertIn("STOP_LOSS", f.read())

    def test_limit_order(self):
        # Place limit long BTC at 40000. Curr price is 50000.
        self.player.place_limit_order("BTC/USDT", "long", 40000.0, 100, 10)
        
        self.assertEqual(len(self.player.orders), 1)
        
        # Update with price 45000 (No trigger)
        self.exchange.get_prices.return_value = {"BTC/USDT": 45000.0}
        self.player.update_portfolio(self.exchange)
        self.assertEqual(len(self.player.orders), 1)
        self.assertEqual(len(self.player.positions), 0)
        
        # Update with price 39000 (Trigger Long)
        self.exchange.get_prices.return_value = {"BTC/USDT": 39000.0}
        self.player.update_portfolio(self.exchange)
        
        self.assertEqual(len(self.player.orders), 0)
        self.assertEqual(len(self.player.positions), 1)
        self.assertIn("BTC/USDT", self.player.positions)
        
        # Verify entry price is execution price (39000), not limit price?
        # Yes, we set it to fill at current price which is better.
        self.assertEqual(self.player.positions["BTC/USDT"]['entry_price'], 39000.0)

if __name__ == '__main__':
    unittest.main()
