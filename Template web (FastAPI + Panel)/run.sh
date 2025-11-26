#!/bin/bash

# Chạy FastAPI
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
python -m uvicorn api_forecast:app --port 8000 --reload 

# Chạy Panel Dashboard
# python -m panel serve dashboard.py --address 0.0.0.0 --port 5006 --autoreload --show
python -m panel serve main_app.py --port 5006 --autoreload --show

python -m panel serve main_app.py --address 0.0.0.0 --port 5006 --allow-websocket-origin={ip-host}:5006 --allow-websocket-origin="*" --autoreload
