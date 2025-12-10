#!/bin/sh
set -e

echo "Starting FastAPI services..."

# API GRU forecast
python -m uvicorn api_forecast:app --host 0.0.0.0 --port 8001 &

# API XGBoost
python -m uvicorn api_XGBoost:app --host 0.0.0.0 --port 8002 &

# API Recommend (ES optimizer)
python -m uvicorn api_recommend:app --host 0.0.0.0 --port 8003 &

echo "Starting Panel dashboard..."

# Panel chạy foreground để giữ container sống
exec python -m panel serve main_app.py \
    --address 0.0.0.0 \
    --port 5006 \
    --allow-websocket-origin="*" \
    --autoreload
