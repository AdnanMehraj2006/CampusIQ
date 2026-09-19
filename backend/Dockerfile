FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps required by some Python packages (bcrypt/psycopg2 build chain)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Run migrations, seed (idempotent), then start uvicorn
CMD ["sh", "-c", "alembic upgrade head && python seed.py --skip-if-populated && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
