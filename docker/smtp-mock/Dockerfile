FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    TZ=UTC

RUN pip install --no-cache-dir fastapi uvicorn email-validator

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8025
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8025"]
