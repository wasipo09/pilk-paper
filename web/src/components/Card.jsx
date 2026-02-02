
import React from 'react';

const Card = ({ pos, onClose }) => {
    const isLong = pos.type === 'long';
    const pnl = (pos.margin + (pos.pnl || 0)) - pos.margin; // Simplified calc for visual
    const isProfitable = pnl >= 0;

    return (
        <div className="card">
            <h3>{pos.feed_symbol?.replace(':USDT', '') || '???'}</h3>
            <div className={`pnl-huge ${isProfitable ? 'text-green' : 'text-red'}`}>
                {isProfitable ? '+' : ''}{pnl.toFixed(2)}
            </div>

            <div className="data-row">
                <span>SIDE</span>
                <span className={isLong ? 'text-green' : 'text-red'}>{pos.type.toUpperCase()}</span>
            </div>
            <div className="data-row">
                <span>SIZE</span>
                <span>{pos.size?.toFixed(4)}</span>
            </div>
            <div className="data-row">
                <span>ENTRY</span>
                <span>{pos.entry_price?.toFixed(2)}</span>
            </div>
            <div className="data-row">
                <span>LIQ</span>
                <span className="text-red">{pos.liq_price?.toFixed(2)}</span>
            </div>

            <button className="big-btn btn-blue" style={{ marginTop: '10px', fontSize: '1rem' }} onClick={onClose}>
                CLOSE
            </button>
        </div>
    );
};

export default Card;
