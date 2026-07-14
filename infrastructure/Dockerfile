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

RUN pip install --no-cache-dir \
    "numpy>=1.26,<2.1" \
    "pandas>=2.0,<2.3" \
    "scikit-learn>=1.3" \
    matplotlib \
    mysql-connector-python \
    python-dotenv \
    yfinance

COPY scripts/ ./scripts/
COPY models/ ./models/
COPY data/processed/ ./data/processed/
COPY sql/ ./sql/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default: retrain leakage-safe models on committed processed features.
CMD ["python", "scripts/predictive_models.py"]
