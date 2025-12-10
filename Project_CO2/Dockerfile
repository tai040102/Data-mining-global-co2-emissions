FROM python:3.10-slim

# Tối ưu log + pip
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Cài các thư viện hệ thống cần cho numpy/pandas/xgboost (build-essential, v.v.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) copy & cài dependencies trước để tận dụng cache
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 2) copy toàn bộ source code vào image
COPY . .

# Panel web port
EXPOSE 5006

# (optional) expose luôn các port API nếu muốn debug từ ngoài
EXPOSE 8001 8002 8003

# script start đã tạo ở bước 2
CMD ["./start.sh"]
