
import axios from 'axios';

const API_URL = '/api'; // Vite proxy will handle this

export const getState = async () => {
    const res = await axios.get(`${API_URL}/state`);
    return res.data;
};

export const executeTrade = async (symbol, action, margin, leverage, tp, sl) => {
    const res = await axios.post(`${API_URL}/trade`, {
        symbol, action, margin, leverage, tp, sl
    });
    return res.data;
};

export const placeLimitOrder = async (symbol, side, price, margin, leverage, tp, sl) => {
    const res = await axios.post(`${API_URL}/order`, {
        symbol, side, price, margin, leverage, tp, sl
    });
    return res.data;
};

export const resetGame = async () => {
    const res = await axios.post(`${API_URL}/reset`);
    return res.data;
};
