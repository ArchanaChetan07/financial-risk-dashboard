FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    libmariadb-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install in stages - core deps first
RUN pip install --no-cache-dir \
    pandas \
    mysql-connector-python \
    sqlalchemy \
    python-dotenv \
    matplotlib \
    seaborn \
    yfinance

# Install ML packages
RUN pip install --no-cache-dir \
    scikit-learn \
    xgboost \
    lightgbm \
    catboost || echo "Some ML packages skipped"

COPY scripts/ ./scripts/
COPY models/ ./models/
COPY sql/ ./sql/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "scripts/data_processing.py"]
