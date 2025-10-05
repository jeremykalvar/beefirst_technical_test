# Simple dev image using Poetry; no dev deps installed in the image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    TZ=UTC

# Install Poetry (no system build tools needed thanks to psycopg[binary])
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

WORKDIR /app

# Leverage cache: copy only manifests first
COPY pyproject.toml poetry.lock* /app/


# Install runtime deps only 
RUN poetry install --no-ansi --no-root

# Source is bind-mounted by compose, but copying doesn’t hurt for first run
COPY . .

RUN chmod +x scripts/wait-for.sh

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
