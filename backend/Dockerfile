FROM python:3.12-slim

WORKDIR /app

ARG INSTALL_DEV=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-dev.txt .
RUN if [ "$INSTALL_DEV" = "1" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY . .

# Produção: Gunicorn + Uvicorn workers (não usar runserver / uvicorn --reload aqui).
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app"]
