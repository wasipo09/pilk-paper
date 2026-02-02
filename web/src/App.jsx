
import { useState, useEffect } from 'react';
import { getState, executeTrade } from './api';
import Card from './components/Card';
import TradeControls from './components/TradeControls';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const state = await getState();
      setData(state);
      setLoading(false);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const handleTrade = async (symbol, action, margin, leverage) => {
    try {
      await executeTrade(symbol, action, margin, leverage);
      fetchData(); // Immediate update
    } catch (e) {
      alert('Trade Failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const closePosition = async (symbol) => {
    try {
      await executeTrade(symbol, 'close');
      fetchData();
    } catch (e) {
      alert('Close Failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  if (!data) return <div className="game-container">Loading...</div>;

  return (
    <>
      <div className="crt-overlay"></div>
      <div className="game-container">
        <div className="header">
          <h1>PILK TRADER</h1>
          <div className="stats-bar">
            <div>BAL: <span className="text-green">${data.balance.toFixed(2)}</span></div>
            <div>EQ: <span className="text-blue">${data.equity.toFixed(2)}</span></div>
          </div>
        </div>

        <div className="card-grid">
          {Object.entries(data.positions).map(([symbol, pos]) => (
            <Card key={symbol} pos={{ ...pos, feed_symbol: pos.feed_symbol || symbol }} onClose={() => closePosition(symbol)} />
          ))}
          {Object.keys(data.positions).length === 0 && (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '2rem', margin: 'auto' }}>
              NO ACTIVE POSITIONS
            </div>
          )}
        </div>

        <TradeControls onTrade={handleTrade} />
      </div>
    </>
  );
}

export default App;
