FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY models/ ./models/
COPY sql/ ./sql/
COPY visualizations/ ./visualizations/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "scripts/data_processing.py"]
