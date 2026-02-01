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
        
        # Mock exchange to return liquidation price
        self.exchange.get_price.return_value = 89.0 # Wiped out
        
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
        # With 4.0 balance and no positions, equity is 4.0
        equity = self.player.update_portfolio(self.exchange)
        self.assertEqual(equity, 4.0)
        self.assertTrue(equity < paper_trader.MIN_EQUITY_GAME_OVER)

if __name__ == '__main__':
    unittest.main()
