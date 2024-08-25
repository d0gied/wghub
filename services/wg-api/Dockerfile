FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# COPY . .

CMD ["python", "app.py"]

