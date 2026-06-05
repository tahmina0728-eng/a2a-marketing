FROM python:3.12-slim

WORKDIR /app

# System deps — Pillow needs libjpeg/zlib for brand image overlay
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install RUNTIME deps — exclude heavy ML packages not needed at runtime
RUN uv sync --frozen --no-dev \
    --no-install-package sentence-transformers \
    --no-install-package torch \
    --no-install-package torchvision \
    --no-install-package torchaudio \
    || uv sync --frozen --no-dev

# Copy application code
COPY main.py ./
COPY app/ ./app/

# Copy brand guidelines (text — small, used when GCS search returns empty)
COPY bucket/brands/Rnorr/Guidelines/    ./bucket/brands/Rnorr/Guidelines/
COPY bucket/brands/Sunglow/Guidelines/  ./bucket/brands/Sunglow/Guidelines/
COPY bucket/brands/Boozt/Guidelines/    ./bucket/brands/Boozt/Guidelines/

# Copy brand fonts (used by Pillow for KV image overlay at runtime)
COPY bucket/brands/Sunglow/Font/  ./bucket/brands/Sunglow/Font/
COPY bucket/brands/Rnorr/Font/    ./bucket/brands/Rnorr/Font/
COPY bucket/brands/Boozt/Font/    ./bucket/brands/Boozt/Font/

ENV PORT=8080
EXPOSE 8080

CMD uv run uvicorn main:app --host 0.0.0.0 --port $PORT
