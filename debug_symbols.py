import ccxt
print("Connecting...")
ex = ccxt.binanceusdm()
ex.load_markets()
print(f"Total symbols: {len(ex.symbols)}")
print("First 10 symbols:", ex.symbols[:10])
if 'BTC/USDT' in ex.symbols:
    print("BTC/USDT exists")
elif 'BTC/USDT:USDT' in ex.symbols:
    print("BTC/USDT:USDT exists")
else:
    print("Neither found. Searching for BTC...")
    print([s for s in ex.symbols if 'BTC' in s][:5])
