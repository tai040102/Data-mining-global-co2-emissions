#!/bin/bash

# Chạy FastAPI
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
python -m uvicorn main:app --port 8000 --reload &

# Chạy Panel Dashboard
# python -m panel serve dashboard.py --address 0.0.0.0 --port 5006 --autoreload --show
python -m panel serve dashboard.py --port 5006 --autoreload --show
