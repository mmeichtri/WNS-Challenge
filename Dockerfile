FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY inputs/ inputs/

EXPOSE 8000

CMD ["sh", "-c", "python -m app.ingestion && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


FROM runtime AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests/ tests/

CMD ["pytest", "-v"]
