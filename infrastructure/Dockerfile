FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY scripts/ ./scripts/
COPY models/ ./models/
COPY sql/ ./sql/
COPY visualizations/ ./visualizations/
COPY .env.example .env.example

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "scripts/data_processing.py"]
