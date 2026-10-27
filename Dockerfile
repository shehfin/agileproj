FROM python:3.13-slim

LABEL org.opencontainers.image.title="product-catalog" \
      org.opencontainers.image.version="v3" \
      student.id="24MIS0175"

# LOW_STOCK_THRESHOLD: products with quantity below this are "low stock".
# Override at run time, e.g. docker run -e LOW_STOCK_THRESHOLD=5 ...
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/products.db \
    LOW_STOCK_THRESHOLD=10

WORKDIR /app

# Install dependencies first so this layer is cached between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as a non-root user; /app/data holds the SQLite file.
RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data
USER appuser

EXPOSE 5000

# Docker marks the container unhealthy if /health stops returning 200.
# (The slim image has no curl, so Python makes the request.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=4)"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
