# Pin the Python minor version: question sets are regenerated from seeds with `random`,
# so a Python upgrade that changes random's algorithms would change already-issued questions.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py questions.py manage.py ./
COPY static ./static

# /data is owned by the app user so a fresh named volume inherits that ownership
RUN useradd --system --uid 1000 app && mkdir -p /data && chown app /data
USER app

EXPOSE 8080
# One worker (threads for concurrency): the secret key file and schema are created at import,
# and multiple worker processes could race on first start.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "app:app"]
