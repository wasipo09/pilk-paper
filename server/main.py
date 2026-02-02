from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
from contextlib import asynccontextmanager
from core import Player, PaperExchange, TradeError

# Global Game State
player = Player()
exchange = PaperExchange()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the game loop
    task = asyncio.create_task(game_loop())
    yield
    # Shutdown
    task.cancel()

app = FastAPI(lifespan=lifespan)

async def game_loop():
    print("Starting Game Loop...")
    while True:
        try:
            # 1 minute tick
            await asyncio.sleep(60) 
            print("Tick: Updating portfolio...")
            # We don't have a console here, so we just run it. 
            # In a real app we might want to broadcast these updates via Websocket
            player.update_portfolio(exchange) 
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in game loop: {e}")

# Models
class TradeRequest(BaseModel):
    symbol: str
    action: str # long, short, close
    margin: float = 0
    leverage: int = 1
    tp: Optional[float] = None
    sl: Optional[float] = None

class LimitOrderRequest(BaseModel):
    symbol: str
    side: str # long, short
    price: float
    margin: float
    leverage: int
    tp: Optional[float] = None
    sl: Optional[float] = None

@app.get("/api/state")
def get_state():
    # Sync prices for display without executing orders (optional, or just return last state)
    # For better UX, we might want to fetch latest prices here too, 
    # but to avoid rate limits let's rely on the 1-min loop OR client polling trigger
    
    # Actually, for the UI to show PnL we need current prices.
    # Let's do a lightweight fetch of held positions only.
    
    portfolio_value = player.update_portfolio(exchange) 
    
    return {
        "balance": player.balance,
        "equity": portfolio_value,
        "positions": player.positions,
        "orders": player.orders,
        "history_file": "history.csv" # The frontend can't read this directly easily unless we serve it
    }

@app.post("/api/trade")
def execute_trade(req: TradeRequest):
    symbol = req.symbol.upper()
    if '/' not in symbol: symbol += "/USDT"
    
    # feeding logging back to stdout for now
    def log(msg, style=""):
        print(f"[{style}]{msg}")

    # Fetch price
    feed_sym, price = exchange.resolve_symbol_and_price(symbol)
    if not price:
        raise HTTPException(status_code=400, detail="Symbol not found or price unavailable")

    try:
        if req.action == 'close':
            player.execute_trade(symbol, 'close', 0, 0, price, log_callback=log)
        else:
            player.execute_trade(
                symbol, 
                req.action, 
                req.margin, 
                req.leverage, 
                price, 
                feed_symbol=feed_sym, 
                tp=req.tp, 
                sl=req.sl, 
                log_callback=log
            )
    except TradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"status": "ok", "balance": player.balance}

@app.post("/api/order")
def place_order(req: LimitOrderRequest):
    symbol = req.symbol.upper()
    if '/' not in symbol: symbol += "/USDT"

    feed_sym, price = exchange.resolve_symbol_and_price(symbol)
    if not feed_sym:
         raise HTTPException(status_code=400, detail="Symbol not found")

    try:
        player.place_limit_order(
            symbol, 
            req.side, 
            req.price, 
            req.margin, 
            req.leverage, 
            feed_symbol=feed_sym,
            tp=req.tp,
            sl=req.sl
        )
    except TradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}

@app.post("/api/reset")
def reset_game():
    global player
    player = Player(reset=True)
    return {"status": "reset", "balance": player.balance}
