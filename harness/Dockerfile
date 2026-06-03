FROM python:3.12-slim

WORKDIR /app

# System deps only — no build tools needed for slim packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install RUNTIME deps only — exclude sentence-transformers (seeding only)
# and other heavy ML packages not needed at runtime
RUN uv sync --frozen --no-dev \
    --no-install-package sentence-transformers \
    --no-install-package torch \
    --no-install-package torchvision \
    --no-install-package torchaudio \
    || uv sync --frozen --no-dev

# Copy application code
COPY main.py ./
COPY app/ ./app/

# Copy only guidelines (not binary assets — loaded from GCS at runtime)
COPY bucket/brands/McDonalds/Guidelines/ ./bucket/brands/McDonalds/Guidelines/
COPY bucket/brands/Rnorr/Guidelines/ ./bucket/brands/Rnorr/Guidelines/
COPY bucket/brands/Sunglow/Guidelines/ ./bucket/brands/Sunglow/Guidelines/
COPY bucket/brands/Boozt/Guidelines/ ./bucket/brands/Boozt/Guidelines/

ENV PORT=8080
EXPOSE 8080

CMD uv run uvicorn main:app --host 0.0.0.0 --port $PORT
