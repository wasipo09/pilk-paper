#!/bin/bash

# Kill background processes on exit
trap "kill 0" EXIT

echo "🎰 STARTING PILK PAPER TRADER WEB UI 🎰"
echo "---------------------------------------"

# 1. Setup Python Environment
if [ ! -d ".venv" ]; then
    echo "🐍 Creating Virtual Environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "📦 Checking Python Dependencies..."
pip install -r requirements.txt > /dev/null

# 2. Setup Node Environment
if [ ! -d "web/node_modules" ]; then
    echo "⚛️  Installing Frontend Dependencies..."
    cd web && npm install && cd ..
fi

# 3. Start Services
echo "🚀 Starting Backend (Port 8000)..."
python3 -m uvicorn server.main:app &

echo "🃏 Starting Frontend..."
cd web && npm run dev &

wait
