
import React, { useState } from 'react';

const TradeControls = ({ onTrade }) => {
    const [symbol, setSymbol] = useState('BTC');
    const [margin, setMargin] = useState(100);
    const [leverage, setLeverage] = useState(10);

    return (
        <div className="controls">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label>SYMBOL</label>
                <input
                    className="big-btn"
                    style={{ width: '100px', background: 'white' }}
                    value={symbol}
                    onChange={e => setSymbol(e.target.value.toUpperCase())}
                />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label>MARGIN</label>
                <input
                    className="big-btn"
                    type="number"
                    style={{ width: '100px', background: 'white' }}
                    value={margin}
                    onChange={e => setMargin(Number(e.target.value))}
                />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label>LEV (x)</label>
                <input
                    className="big-btn"
                    type="number"
                    style={{ width: '80px', background: 'white' }}
                    value={leverage}
                    onChange={e => setLeverage(Number(e.target.value))}
                />
            </div>

            <button className="big-btn btn-green" onClick={() => onTrade(symbol, 'long', margin, leverage)}>
                BUY (LONG)
            </button>
            <button className="big-btn btn-red" onClick={() => onTrade(symbol, 'short', margin, leverage)}>
                SELL (SHORT)
            </button>
        </div>
    );
};

export default TradeControls;
