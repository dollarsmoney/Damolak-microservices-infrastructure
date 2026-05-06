# ── Multi-stage build: Data Service (Python/FastAPI) ──
FROM python:3.12-slim AS production

RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

COPY app/ ./app/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENV ENVIRONMENT=production PORT=8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
